from Parser import parser as parser
from Parser import RDDLReader as RDDLReader
import Grounder.RDDLGrounder as RDDLGrounder
from Simulator.RDDLSimulator import RDDLSimulator

DOMAIN = 'power_unit_commitment.rddl'

# DOMAIN = 'ThiagosReservoir.rddl'
# DOMAIN = 'Thiagos_Mars_Rover.rddl'
# DOMAIN = 'dbn_prop.rddl'
# DOMAIN = 'RamMod_Thiagos_HVAC.rddl'
DOMAIN = 'RamMod_smaller_Thiagos_HVAC.rddl'
# DOMAIN = 'RamMod_Thiagos_HVAC_grounded.rddl'

# DOMAIN = 'Thiagos_HVAC.rddl'
# DOMAIN = 'Thiagos_HVAC_grounded.rddl'
# DOMAIN = 'wildfire_mdp.rddl'


def main():

    MyReader = RDDLReader.RDDLReader('RDDL/' + DOMAIN)
    # MyReader = RDDLReader.RDDLReader('RDDL/power_unit_commitment_domain.rddl',
    #                                  'RDDL/power_unit_commitment_instance.rddl')
    domain = MyReader.rddltxt

    MyLexer = parser.RDDLlex()
    MyLexer.build()
    MyLexer.input(domain)
    # [token for token in MyLexer._lexer]

    # build parser - built in lexer, non verbose
    MyRDDLParser = parser.RDDLParser(None, False)
    MyRDDLParser.build()

    # parse RDDL file
    rddl_ast = MyRDDLParser.parse(domain)

    # MyXADDTranslator = XADDTranslator(rddl_ast)
    # MyXADDTranslator.Translate()

    from pprint import pprint
    grounder = RDDLGrounder.RDDLGroundedGrounder(rddl_ast)
    model = grounder.Ground()
    pprint(vars(model))
    
    good_policy = True
    sampler = RDDLSimulator(model)
    loops = 1
    
    print('\nstarting simulation')
    for h in range(loops):
        state = sampler.reset_state()
        total_reward = 0.
        for _ in range(2000):
            sampler.check_state_invariants()
            sampler.check_action_preconditions()
            actions = {'AIR_r1': 0., 'AIR_r2': 0., 'AIR_r3': 0.}
            if good_policy:
                if state['TEMP_r1'] < 20.5:
                    actions['AIR_r1'] = 5.
                if state['TEMP_r2'] < 20.5:
                    actions['AIR_r2'] = 5.
                if state['TEMP_r3'] < 20.5:
                    actions['AIR_r3'] = 5.
                if state['TEMP_r1'] > 23.:
                    actions['AIR_r1'] = 0.
                if state['TEMP_r2'] > 23.:
                    actions['AIR_r2'] = 0.
                if state['TEMP_r3'] > 23.:
                    actions['AIR_r3'] = 0.
            state = sampler.sample_next_state(actions)
            reward = sampler.sample_reward()
            sampler.update_state()
            if h == 0:
                print('state = {}'.format(state))
                print('reward = {}'.format(reward))
                print('derived = {}'.format(model.derived))
                print('interm = {}'.format(model.interm))
                print('')
            total_reward += reward
        print('trial {}, total reward {}'.format(h, total_reward))
        
    # grounder = RDDLGrounder.RDDLGrounder(rddl_ast)
    # grounder.Ground()
    # pprint(vars(grounder))
    
    # grounder.InitGround()

    grounder2 = RDDLGrounder.RDDLGrounder(rddl_ast)
    model2 = grounder2.Ground()


    # generator = RDDLGenerator.RDDLGenerator(rddl_ast)
    # rddl = generator.GenerateRDDL()
    

    print("reached end of test.py")

if __name__ == "__main__":
    main()

