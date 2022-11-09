import jax
import jax.random as random
import numpy as np
from typing import Dict
import warnings

from pyRDDLGym.Core.ErrorHandling.RDDLException import RDDLActionPreconditionNotSatisfiedError
from pyRDDLGym.Core.ErrorHandling.RDDLException import RDDLInvalidExpressionError
from pyRDDLGym.Core.ErrorHandling.RDDLException import RDDLStateInvariantNotSatisfiedError
from pyRDDLGym.Core.Jax.JaxRDDLCompiler import JaxRDDLCompiler
from pyRDDLGym.Core.Parser.rddl import RDDL
from pyRDDLGym.Core.Parser.expr import Value
from pyRDDLGym.Core.Simulator.RDDLSimulator import RDDLSimulator

Args = Dict[str, Value]


class JaxRDDLSimulator(RDDLSimulator):
    
    DEFAULT_VALUES = {
        'int': 0,
        'real': 0.0,
        'bool': False
    }
    
    def __init__(self, rddl: RDDL, key: random.PRNGKey, soft_error: bool=True) -> None:
        self.rddl = rddl
        self.key = key
        self.soft = soft_error
        
        self.compiler = JaxRDDLCompiler(rddl)
        data = self.compiler.compile()
        self.invariants = data['invariants']
        self.preconds = data['preconds']
        self.terminals = data['terminals']
        _, self.reward = data['reward']
        _, self.cpfs = data['cpfs']
        
        # initialization of scalar and pvariables tensors
        rev_objects = {}          
        self.init_values = {}
        for obj, values in rddl.non_fluents.objects:
            rev_objects.update(zip(values, [obj] * len(values)))   
        for pvar in rddl.domain.pvariables:
            name = pvar.name
            params = pvar.param_types
            if params is None:
                if pvar.default is not None:
                    self.init_values[name] = pvar.default
                elif pvar.range in JaxRDDLSimulator.DEFAULT_VALUES:
                    self.init_values[name] = JaxRDDLSimulator.DEFAULT_VALUES[pvar.range]
                else:
                    raise Exception('Internal error: type {} is not recognized.'.format(pvar.range))
            else:
                self.init_values[name] = np.zeros(
                    shape=tuple(len(self.compiler.objects[p]) for p in params))  
        if hasattr(rddl.non_fluents, 'init_non_fluent'): 
            for (name, params), value in rddl.non_fluents.init_non_fluent:
                if params is not None:
                    coords = tuple(self.compiler.objects[rev_objects[p]][p] for p in params)
                    self.init_values[name][coords] = value                
        self.subs = self.init_values.copy()
        
    @staticmethod
    def _print_stack_trace(expr, subs, key):
        return str(jax.make_jaxpr(expr)(subs, key))
    
    def handle_error_code(self, code, aux_str):
        code = reversed(bin(code)[2:])
        errors = [JaxRDDLCompiler.INVERSE_ERROR_CODES[i]
                  for i, c in enumerate(code) if c == '1']
        if errors:
            error_message = 'Internal error(s) returned from Jax evaluation of {}:\n'.format(
                    aux_str) + '\n'.join(
                        '{}. {}'.format(i + 1, s) for i, s in enumerate(errors))
            if self.soft:
                warnings.warn(error_message, FutureWarning, stacklevel=2)
            else:
                raise RDDLInvalidExpressionError(error_message)
    
    def _check_state_invariants(self) -> None:
        '''Throws an exception if the state invariants are not satisfied.'''
        for idx, invariant in enumerate(self.invariants):
            sample, self.key, error = invariant(self.subs, self.key)
            self.handle_error_code(error, 'invariant {}'.format(idx + 1))
            if not bool(sample):
                raise RDDLStateInvariantNotSatisfiedError(
                    'State invariant {} is not satisfied.'.format(idx + 1) + 
                    '\n' + JaxRDDLSimulator._print_stack_trace(invariant, self.subs, self.key))
    
    def check_action_preconditions(self) -> None:
        '''Throws an exception if the action preconditions are not satisfied.'''
        for idx, precond in enumerate(self.preconds):
            sample, self.key, error = precond(self.subs, self.key)
            self.handle_error_code(error, 'precondition {}'.format(idx + 1))
            if not bool(sample):
                raise RDDLActionPreconditionNotSatisfiedError(
                    'Action precondition {} is not satisfied.'.format(idx + 1) + 
                    '\n' + JaxRDDLSimulator._print_stack_trace(precond, self.subs, self.key))
    
    def check_terminal_states(self) -> bool:
        '''return True if a terminal state has been reached.'''
        for idx, terminal in enumerate(self.terminals):
            sample, self.key, error = terminal(self.subs, self.key)
            self.handle_error_code(error, 'termination {}'.format(idx + 1))
            if bool(sample):
                return True
        return False
    
    def sample_reward(self) -> float:
        '''Samples the current reward given the current state and action.'''
        reward, self.key, error = self.reward(self.subs, self.key)
        self.handle_error_code(error, 'reward function')
        return float(reward)
    
    def reset(self) -> Args:
        '''Resets the state variables to their initial values.'''
        self.subs = self.init_values.copy()  
        obs = {var: self.subs[var] for var in self.compiler.states.values()}
        done = self.check_terminal_states()    
        return obs, done
    
    def step(self, actions: Args) -> Args:
        '''Samples and returns the next state from the cpfs.
        
        :param actions: a dict mapping current action fluents to their values
        '''
        subs = self.subs 
        subs.update(actions)
        
        cpf_order = self.rddl.domain.derived_cpfs + \
                    self.rddl.domain.intermediate_cpfs + \
                    self.rddl.domain.state_cpfs + \
                    self.rddl.domain.observation_cpfs 
                    
        for cpf in cpf_order:
            name = cpf.pvar[1][0]
            subs[name], self.key, error = self.cpfs[name](subs, self.key)
            self.handle_error_code(error, 'CPF <{}>'.format(name))
        next_subs = subs.copy()
        for cpf in self.cpfs.keys():
            unprimed = self.compiler.states.get(cpf, cpf)
            next_subs[unprimed] = subs[cpf]

        obs = {var: next_subs[var] for var in self.compiler.states.values()}
        reward = self.sample_reward()
        self.subs = next_subs
        done = self.check_terminal_states()
        return obs, reward, done
        
