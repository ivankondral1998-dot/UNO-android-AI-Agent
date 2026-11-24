# R5.4 Candidate / erratum 12: S6 offline gradient reference

Scope: Astra `01_MATH_CANDIDATE_RU.md` §6, `02_ERRATA_RU.md` item 12, fixed support and ideal smooth probability law. Existing TRAIN001 is fixed K=2 and uses no learned S6; its loss/checkpoints are unchanged. This module provides an offline PyTorch gradient surrogate, not a new architecture, optimizer, product policy or trained head.

For cyclic admissible prefixes q=1..m, a_q=sum(rotated logits[:q])/sqrt(q), s=softmax(a/T), p=(1-epsilon)s+epsilon/m. Differentiate the marginal log probability (not the explore branch). The factor on the softmax score is (1-epsilon)*s_q/p_q. Forced prefix, cap and budget stop have zero score. A learnable interior Bernoulli hazard is evaluated after a real S5 step, not before it. Fixed endpoints may be represented by omitting the decision, not by differentiating log(0).

For each decision j: construct the baseline from the history available before j; use G_j consisting of future loss plus any allowed earlier terms (subtracting only costs already determined). `score_objective` adds detach(G_j-b_j)*(logp_j-detach(logp_j)) to the ordinary path loss. This preserves the reported path loss value but changes its gradient. Direct derivatives remain in the original loss. Baseline parameters are not trained by this surrogate. The caller must establish causal provenance; the helper cannot infer it from arbitrary tensors. A learned baseline can have a separate regression objective under its own contract. No optimizer is invoked.

Proof: on finite fixed support with differentiable probabilities and positive selected mass, differentiating the finite sum over paths yields the direct derivative and sum of decision scores. For each preceding history the score's conditional mean is zero because its probabilities sum to one; a baseline measurable in that history may be subtracted. A baseline depending on a later decision or the current sampled action lacks this cancellation. The finite zero-loss witness in Astra gives -0.21 for a wrong shared baseline, versus 0 for the causal estimator.

Runtime parity: `UnoS6Sampler.prefixWeights` is the unchanged code formerly inline in choosePrefix; the parity test obtains its weights using actual feasible(budget). It emits 96 cases (4 rotations, 4 admissible counts, 3 epsilons, 2 temperatures). Python compares the probabilities and all 960 derivatives against independent scalar finite differences. Five possible paths of a tiny S5-form recurrent witness exercise shared parameters, different feasible step caps, state-dependent hazards and direct plus score derivatives. It is not a full F training test. The JVM tests also check forced and fixed endpoint halts consume no random word. Existing adaptive S6 tests are rerun.

Limits: ideal conditional probability law is not exact finite-word RNG/CDF law; no claim about arbitrary seeds, rejection exhaustion, abort selection bias, support changes, quantization, TBPTT, STE or deployment. FP64 helper rejects unrepresentable intermediate scores and softmax underflow for nontrivial mixtures, rejects saturated trainable hazards. Gradient arithmetic still requires finite-gradient validation before any optimizer. The production S6 heads, actual trace-to-graph reconstruction, complete credit assignment across events, training data, optimizer/weight export and device validation remain open. No proof of descent or useful learning follows from these checks.

Run from repository root (JDK/Kotlin/PyTorch CPU):
```
bash android/scripts/host_verify.sh > host_verify.log
python research/train001/recovered-rtx/s6_policy_gradient_test.py host_verify.log
```
