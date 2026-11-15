"""Minimum causal chronology. Header indexes are structural; neural reads never call neighbor()."""
from dataclasses import dataclass
import math

@dataclass
class Record:
    sequence:int
    ordinal:int
    slot:float
    version:int
    previous:int|None
    next:int|None
    previous_version:int|None
    key:object
    value:object

class Chronology:
    def __init__(self):self.records=[];self.by_id={};self.by_slot={}
    def append(self,sequence,slot,key,value):
        if not isinstance(sequence,int) or sequence<=0 or not math.isfinite(slot) or (self.records and sequence<=self.records[-1].sequence):raise ValueError('NONCAUSAL_WRITE')
        history=self.by_slot.get(slot,[]);previous=self.records[-1] if self.records else None
        record=Record(sequence,len(self.records)+1,slot,len(history)+1,previous.sequence if previous else None,None,history[-1].sequence if history else None,key,value)
        if previous:previous.next=sequence
        self.records.append(record);self.by_id[sequence]=record;self.by_slot.setdefault(slot,[]).append(record)
        return record
    def neighbor(self,anchor,relation):
        if relation=='last':return self.records[-1] if self.records else None
        if relation not in ('previous','next','previous_version'):raise ValueError('UNKNOWN_RELATION')
        record=self.by_id.get(anchor)
        return self.by_id.get(getattr(record,relation)) if record else None
    def history(self,slot):return tuple(self.by_slot.get(slot,()))
    @staticmethod
    def clock(sequence,ordinal,version,reference):
        # Immutable at write, no future record count or label. Dataset bound: <=96 events, <=4 writes.
        u=ordinal/4.;t=sequence/96.;v=version/4.
        if not (0<u<=1 and 0<t<=1 and 0<v<=1):raise ValueError('CLOCK_GEOMETRY')
        return reference.new_tensor([u, u*u, t, t*t, v, v*v, 1., -1.]*16)
