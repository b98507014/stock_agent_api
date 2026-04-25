import os
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from RL_simulator import StockTradingEnv


def make_env():
    return StockTradingEnv()


def train_ppo(model_path='models/ppo_stock_model.zip',
              best_model_dir='models/best',
              log_dir='logs',
              total_timesteps=200000,
              checkpoint_freq=25000,
              eval_freq=25000,
              n_eval_episodes=5):
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    os.makedirs(best_model_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    env = DummyVecEnv([make_env])
    eval_env = DummyVecEnv([make_env])

    checkpoint_callback = CheckpointCallback(save_freq=checkpoint_freq,
                                             save_path=os.path.dirname(model_path),
                                             name_prefix='ppo_stock_checkpoint')

    eval_callback = EvalCallback(eval_env,
                                 best_model_save_path=best_model_dir,
                                 log_path=os.path.join(log_dir, 'eval'),
                                 eval_freq=eval_freq,
                                 n_eval_episodes=n_eval_episodes,
                                 deterministic=True,
                                 render=False)

    policy_kwargs = dict(
        net_arch=[dict(pi=[256, 256], vf=[256, 256])]
    )

    if os.path.exists(model_path):
        print(f"Loading existing PPO model from {model_path}")
        model = PPO.load(model_path, env=env, custom_objects={"learning_rate": 2.5e-4})
    else:
        model = PPO(
            'MlpPolicy',
            env,
            verbose=1,
            tensorboard_log=log_dir,
            n_steps=2048,
            batch_size=64,
            learning_rate=2.5e-4,
            gamma=0.99,
            gae_lambda=0.95,
            ent_coef=0.01,
            clip_range=0.2,
            policy_kwargs=policy_kwargs,
        )

    print(f"Starting PPO training for {total_timesteps} timesteps...")
    model.learn(total_timesteps=total_timesteps,
                callback=[checkpoint_callback, eval_callback])
    model.save(model_path)
    print(f"PPO training completed and final model saved to {model_path}")
    print(f"Best evaluation models are saved in {best_model_dir}")

    return model, env


def evaluate_model(model, env, n_eval_episodes=5):
    print(f"Evaluating model for {n_eval_episodes} episodes...")
    for episode in range(1, n_eval_episodes + 1):
        reset_result = env.reset()
        obs = reset_result[0] if isinstance(reset_result, tuple) else reset_result
        done = False
        episode_reward = 0.0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            step_result = env.step(action)
            if len(step_result) == 5:
                obs, reward, terminated, truncated, info = step_result
            else:
                obs, reward, done, info = step_result
                terminated = done
                truncated = False
            done = terminated or truncated
            episode_reward += float(reward)
        print(f"Episode {episode}: total reward = {episode_reward:.2f}")


if __name__ == '__main__':
    model, env = train_ppo(total_timesteps=200000)
    evaluate_model(model, env, n_eval_episodes=5)
