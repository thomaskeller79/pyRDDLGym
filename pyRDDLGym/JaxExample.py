import sys

from pyRDDLGym.Planner import JaxConfigManager
  

def slp_no_replan(env):
    myEnv, planner, train_args = JaxConfigManager.get(f'{env}.cfg')
    
    for callback in planner.optimize(**train_args):
        print('step={} train_return={:.6f} test_return={:.6f}'.format(
              str(callback['iteration']).rjust(4),
              callback['train_return'],
              callback['test_return']))
    plan = planner.get_plan(callback['params'])
    
    total_reward = 0
    state = myEnv.reset()
    for step in range(myEnv.horizon):
        # myEnv.render()
        action = plan[step]
        next_state, reward, done, _ = myEnv.step(action)
        total_reward += reward 
        print()
        print('step       = {}'.format(step))
        print('state      = {}'.format(state))
        print('action     = {}'.format(action))
        print('next state = {}'.format(next_state))
        print('reward     = {}'.format(reward))
        state = next_state
        if done:
            break        
    print(f'episode ended with reward {total_reward}')
    myEnv.close()

    
def slp_replan(env):
    myEnv, planner, train_args = JaxConfigManager.get(f'{env}.cfg')
    
    total_reward = 0
    state = myEnv.reset()
    for step in range(myEnv.horizon):
        # myEnv.render()
        * _, callback = planner.optimize(**train_args, init_subs=myEnv.sampler.subs)
        action = planner.get_plan(callback['params'])[0]
        next_state, reward, done, _ = myEnv.step(action)
        total_reward += reward 
        print()
        print('step       = {}'.format(step))
        print('state      = {}'.format(state))
        print('action     = {}'.format(action))
        print('next state = {}'.format(next_state))
        print('reward     = {}'.format(reward))
        state = next_state
        if done:
            break
    print(f'episode ended with reward {total_reward}')
    myEnv.close()

    
def main(env, replan):
    if replan:
        slp_replan(env)
    else: 
        slp_no_replan(env)
    
        
if __name__ == "__main__":
    if len(sys.argv) < 2:
        args = [sys.argv[0]] + ['UAV continuous']
    else:
        args = sys.argv
    env = args[1]
    replan = env.endswith('replan')
    main(env, replan)
