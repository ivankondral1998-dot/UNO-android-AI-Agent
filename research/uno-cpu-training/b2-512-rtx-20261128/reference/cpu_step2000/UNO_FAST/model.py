"""Astra S4(empty)/S5 and tied text output, in the fixed text-only domain."""
import torch
from torch import nn
from torch.nn import functional as F

from train001_backend import decoded_row_guard
from fast_projection import project


class LanguageF(nn.Module):
    def __init__(self, vocab, width=512):
        super().__init__()
        if width < 64 or width % 64:
            raise ValueError("B2 block width is 64")
        self.width = width
        blocks = width // 64
        self.rules = {}
        self.E = self.matrix("E", (vocab, width), 8, width, 32768)
        self.Us = self.matrix("Us", (width, width), 1, width, width)
        self.A = self.matrix("A", (2, blocks, 256, width), 1, width, 256)
        self.C = self.matrix("C", (2, blocks, 256, width), 2, width, 256)
        self.B = self.matrix("B", (2, blocks, 64, 256), .9, 256, 64)
        self.bias("e", (width,), 1)
        self.bias("bz", (width,), 1)
        self.bias("a", (2, blocks, 256), 8)
        self.bias("b", (2, blocks, 64), 8)
        self.bias("b_text", (vocab,), 8)
        nn.init.uniform_(self.e, -.01, .01)
        self.project_()

    def matrix(self, name, shape, cap, fan_in, fan_out):
        x = nn.Parameter(torch.empty(shape))
        bound = (6. / (fan_in + fan_out)) ** .5
        nn.init.uniform_(x, -bound, bound)
        self.rules[name] = cap, False
        return x

    def bias(self, name, shape, cap):
        self.register_parameter(name, nn.Parameter(torch.zeros(shape)))
        self.rules[name] = cap, True

    @torch.no_grad()
    def project_(self):
        for name, p in self.named_parameters():
            cap, box = self.rules[name]
            if box:
                if not bool(torch.isfinite(p).all()):
                    raise ValueError(f"nonfinite parameter: {name}")
                p.clamp_(-cap, cap)
            else:
                # Each chunk's projection checks finite input and decoded output.
                # Any failure aborts the update before checkpoint publication.
                for rows in p.view(-1, p.shape[-1]).split(512):
                    project(rows, cap)

    @torch.no_grad()
    def validate(self):
        for name, p in self.named_parameters():
            cap, box = self.rules[name]
            if box:
                ok = p.double().abs() <= cap
            else:
                ok = p.double().abs().sum(-1) <= decoded_row_guard(cap, p.shape[-1])
            if not bool(ok.all()):
                raise ValueError(f"nonfinite or decoded norm outside cap: {name}")

    def event(self, token, state):
        # R5.3 S4: goal/metadata zero, bank empty. S5: q=all blocks, K=1.
        z0 = torch.tanh(self.E[token] + self.Us @ state + self.e + self.bz)
        z = torch.tanh(z0)
        h0 = .5 * state + .5 * z
        u = torch.tanh(self.A @ h0 + self.C @ z + self.a)
        proposal = torch.tanh((self.B @ u.unsqueeze(-1)).squeeze(-1) + self.b)
        return .5 * h0 + .5 * proposal.mean(0).reshape(self.width)

    def forward(self, tokens, state):
        states = []
        for token in tokens.unbind():
            state = self.event(token, state)
            states.append(state)
        return F.linear(torch.stack(states), self.E, self.b_text), state
