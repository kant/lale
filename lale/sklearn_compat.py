# Copyright 2019 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Any, Dict, Optional, List, Set
import random
import math
import warnings

import lale.operators as Ops
from lale.pretty_print import hyperparams_to_string
from lale.search.PGO import remove_defaults_dict

# This method (and the to_lale() method on the returned value)
# are the only ones intended to be exported
def make_sklearn_compat(op:'Ops.Operator')->'SKlearnCompatWrapper':
    """Top level function for providing compatibiltiy with sklearn operations
       This returns a wrapper around the provided sklearn operator graph which can be passed
       to sklearn methods such as clone and GridSearchCV
       The wrapper may modify the wrapped lale operator/pipeline as part of providing
       compatibility with these methods.
       After the sklearn operation is complete, 
       SKlearnCompatWrapper.to_lale() can be called to recover the 
       wrapped lale operator for future use
    """
    return SKlearnCompatWrapper.make_wrapper(op)

class WithoutGetParams(object):
    """ This wrapper forwards everything except "get_attr" to what it is wrapping
    """
    def __init__(self, base):
        self._base = base
        assert self._base != self

    def __getattr__(self, name):
        # This is needed because in python copy skips calling the __init__ method
        if name == "_base":
            raise AttributeError
        if name == 'get_params':
            raise AttributeError
        else:
            return getattr(self._base, name)

def partition_sklearn_params(d:Dict[str, Any])->Dict[str, Dict[str, Any]]:
    ret:Dict[str, Dict[str, Any]] = {}
    for k, v in d.items():
        ks = k.split("__", 1)
        assert len(ks) == 2
        bucket:Dict[str, Any] = {}
        group:str = ks[0]
        param:str = ks[1]
        if group in ret:
            bucket = ret[group]
        else:
            ret[group] = bucket
        assert param not in bucket
        bucket[param] = v
    return ret

# TODO: we should be able enrich this type to Ops.TrainableOperator
def set_operator_params(op:'Ops.Operator', **impl_params)->Ops.Operator:
    """May return a new operator, in which case the old one should be overwritten
    """
    if isinstance(op, Ops.PlannedIndividualOp):
        return op.set_params(**impl_params)
    elif isinstance(op, Ops.Pipeline):
        steps = op.steps()
        partitioned_params:Dict[str,Dict[str, Any]] = partition_sklearn_params(impl_params)
        found_names:Set[str] = set()
        step_map:Dict[Ops.Operator, Ops.Operator] = {}
        for s in steps:
            name = s.name()
            found_names.add(name)
            if name in partitioned_params:
                params = partitioned_params[name]
                new_s = set_operator_params(s, **params)
                if s != new_s:
                    step_map[s] = new_s
        # make sure that no parameters were passed in for operations
        # that are not actually part of this pipeline
        assert set(partitioned_params.keys()).issubset(found_names)
        if step_map:
            op.subst_steps(step_map)
            if not isinstance(op, Ops.TrainablePipeline):
                # As a result of choices made, we may now be a TrainableIndividualOp
                return Ops.get_pipeline_of_applicable_type(op.steps(), op.edges(), ordered=True)
            else:
                return op
        else:
            return op
    elif isinstance(op, Ops.OperatorChoice):
        discriminant_name:str = "_lale_discriminant"
        assert discriminant_name in impl_params
        choice_name = impl_params[discriminant_name]
        choices:List[Ops.Operator] = [step for step in op.steps() if step.name() == choice_name]
        assert len(choices)==1, f"found {len(choices)} operators with the same name: {choice_name}"
        choice:Ops.Operator = choices[0]
        chosen_params = dict(impl_params)
        del chosen_params[discriminant_name]

        new_step = set_operator_params(choice, **chosen_params)
        # we remove the OperatorChoice, replacing it with the branch that was taken
        return new_step
    else:
        assert False, f"Not yet supported operation of type: {op.__class__.__name__}"

class SKlearnCompatWrapper(object):
    _base:WithoutGetParams

    @classmethod
    def make_wrapper(cls, base:'Ops.Operator'):
        b:Any = base
        if isinstance(base, SKlearnCompatWrapper):
            return base
        elif not isinstance(base, WithoutGetParams):
            b = WithoutGetParams(base)
        return cls(__lale_wrapper_base=b)

    def __init__(self, **kwargs):
        self._base = kwargs['__lale_wrapper_base']
        assert self._base != self

    def to_lale(self)->Ops.Operator:
        cur:Any = self
        assert cur != None
        assert cur._base != None
        cur = cur._base
        while isinstance(cur, WithoutGetParams):
            cur = cur._base
        assert isinstance(cur, Ops.Operator)
        return cur

    # sklearn calls __repr__ instead of __str__
    def __repr__(self):
        op = self.to_lale()
        if isinstance(op, Ops.TrainableIndividualOp):
            name = op.name()
            hyps = hyperparams_to_string(op.hyperparams())
            return name + "(" + hyps + ")"
        else:
            return super().__repr__()

    def __getattr__(self, name):
        # This is needed because in python copy skips calling the __init__ method
        if name == "_base":
            raise AttributeError
        return getattr(self._base, name)


    def get_params(self, deep:bool = True)->Dict[str,Any]:
        out:Dict[str,Any] = {}
        if not deep:
            out['__lale_wrapper_base'] = self._base
        else:
            pass #TODO
        return out

    def fit(self, X, y=None, **fit_params):
        if hasattr(self._base, 'fit'):
            filtered_params = remove_defaults_dict(fit_params)
            return self._base.fit(X, y=y, **filtered_params)
        else:
            pass

    def set_params(self, **impl_params):

        if '__lale_wrapper_base' in impl_params:
            self._base = impl_params['__lale_wrapper_base']
            assert self._base != self
        else:
            prev = self
            cur = self._base
            assert prev != cur
            assert cur != None
            while isinstance(cur, WithoutGetParams):
                assert cur != cur._base
                prev = cur
                cur = cur._base
            if not isinstance(cur, Ops.Operator):
                assert False
            assert isinstance(cur, Ops.Operator)
            new_s = set_operator_params(cur, **impl_params)
            if new_s != cur:
                prev._base = new_s                
        return self

