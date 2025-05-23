# -*- coding: utf-8 -*-

import gym
from gym import spaces
import numpy as np

class VolcanoCrossingEnv(gym.Env):
    def __init__(self, grid_size=(4, 4), start=(0, 0), goal=None, crater_prob=0.2, slip_probability=0.0):
        super(VolcanoCrossingEnv, self).__init__()

        self.grid_size = grid_size
        self.start = start
        self.goal = goal if goal is not None else (grid_size[0] - 1, grid_size[1] - 1)
        self.crater_prob = crater_prob
        self.slip_probability = slip_probability

        self.action_space = spaces.Discrete(4)  # Up, Down, Left, Right
        self.observation_space = spaces.Discrete(np.prod(grid_size))

        self.state = None
        self.steps_taken = 0
        self.terminal_states = {self.goal}  # Set the goal as the terminal state

        self._generate_grid()

    def _generate_grid(self):
        self.grid = np.zeros(self.grid_size)
        self.grid[self.start] = 1  # Agent's starting position
        self.grid[self.goal] = 2  # Goal position

        for i in range(self.grid_size[0]):
            for j in range(self.grid_size[1]):
                if np.random.rand() < self.crater_prob and (i, j) != self.start and (i, j) != self.goal:
                    self.grid[i, j] = -20  # Crater

    def reset(self):
        self.state = self.start
        self.steps_taken = 0
        return self.state

    def step(self, action):
        # Incorporate slip probability
        if np.random.rand() < self.slip_probability:
            action = np.random.choice(self.action_space.n)

        if action == 0:  # Up
            new_state = (self.state[0] - 1, self.state[1])
        elif action == 1:  # Down
            new_state = (self.state[0] + 1, self.state[1])
        elif action == 2:  # Left
            new_state = (self.state[0], self.state[1] - 1)
        elif action == 3:  # Right
            new_state = (self.state[0], self.state[1] + 1)

        self.steps_taken += 1

        if 0 <= new_state[0] < self.grid_size[0] and 0 <= new_state[1] < self.grid_size[1]:
            if self.grid[new_state] == -20:  # Agent stepped on a crater
                reward = -10
                done = True
            elif self.grid[new_state] == 2:  # Agent reached the goal
                reward = 10
                done = True
            else:
                reward = -1
                done = False

            self.state = new_state
        else:
            reward = -1
            done = False

        if self.steps_taken >= np.prod(self.grid_size) or self.state in self.terminal_states:
            done = True

        return self.state, reward, done, {}

    def render(self):
        print(self.grid)


# Model-free Monte Carlo Algorithm with Epsilon-Greedy Exploration
def monte_carlo_epsilon_greedy(episodes, slip_probability, grid_size, epsilon):
    env = VolcanoCrossingEnv(grid_size=grid_size, slip_probability=slip_probability)
    n_actions = env.action_space.n
    Q = {}  # Q-values table
    returns_count = {}  # Count of returns for each state-action pair

    for episode in range(episodes):
        state = env.reset()
        episode_states = []
        episode_actions = []
        episode_rewards = []

        # Generate an episode using an epsilon-greedy policy
        while True:
            # Epsilon-greedy action selection
            if np.random.rand() < epsilon or state not in Q:
                action = np.random.choice(n_actions)
            else:
                action = np.argmax(Q[state])

            next_state, reward, done, _ = env.step(action)

            episode_states.append(state)
            episode_actions.append(action)
            episode_rewards.append(reward)

            if done:
                break

            state = next_state

        # Update Q-values using Monte Carlo method
        G = 0
        for t in reversed(range(len(episode_states))):
            state_t = episode_states[t]
            action_t = episode_actions[t]
            reward_t = episode_rewards[t]

            G = reward_t + G

            if state_t not in Q:
                Q[state_t] = np.zeros(n_actions)
                returns_count[state_t] = np.zeros(n_actions)

            if state_t not in env.terminal_states:
                returns_count[state_t][action_t] += 1
                Q[state_t][action_t] = (Q[state_t][action_t] + G) / returns_count[state_t][action_t]  # Update average Q-value

    return Q, returns_count


def sarsa(episodes, slip_probability, grid_size, epsilon, alpha=0.1, gamma=0.9):
    env = VolcanoCrossingEnv(grid_size=grid_size, slip_probability=slip_probability)
    n_actions = env.action_space.n
    state_size = np.prod(grid_size)
    Q = {}  # Initialize Q-values table as a dictionary
    returns_count = np.zeros((state_size, n_actions))  # Count of returns for each state-action pair

    for episode in range(episodes):
        state = env.reset()
        action = epsilon_greedy_policy(Q, state, epsilon, n_actions)

        while True:
            next_state, reward, done, _ = env.step(action)
            next_action = epsilon_greedy_policy(Q, next_state, epsilon, n_actions)

            # Convert states to integers for dictionary indexing
            state_int = state[0] * grid_size[1] + state[1]
            next_state_int = next_state[0] * grid_size[1] + next_state[1]

            # Initialize Q-values and returns count for new states
            if state_int not in Q:
                Q[state_int] = np.zeros(n_actions)
            if next_state_int not in Q:
                Q[next_state_int] = np.zeros(n_actions)

            # Ensure returns_count array is initialized for the state-action pair
            if state_int >= returns_count.shape[0] or next_state_int >= returns_count.shape[0]:
                returns_count = np.pad(returns_count, ((0, max(state_int, next_state_int) + 1 - returns_count.shape[0]), (0, 0)))

            # SARSA update
            Q[state_int][action] += alpha * (reward + gamma * Q[next_state_int][next_action] - Q[state_int][action])

            # Update returns count for the visited state-action pair
            returns_count[state_int, action] += 1  # Modified this line inside the loop

            if done:
                break

            state = next_state
            action = next_action

    return Q, returns_count




# Q-learning algorithm
def q_learning_with_average_utility(episodes, slip_probability, grid_size, alpha, gamma, epsilon):
    env = VolcanoCrossingEnv(grid_size=grid_size, slip_probability=slip_probability)
    n_actions = env.action_space.n
    Q = np.zeros((np.prod(grid_size), n_actions))  # Q-values table
    returns_count = np.zeros_like(Q)  # Count of updates for each state-action pair

    for episode in range(episodes):
        state = env.reset()
        while True:
            # Epsilon-greedy action selection
            if np.random.rand() < epsilon or np.sum(Q[state]) == 0:
                action = np.random.choice(n_actions)
            else:
                action = np.argmax(Q[state])
            next_state, reward, done, _ = env.step(action)
            # Q-value update
            Q[state, action] = (1 - alpha) * Q[state, action] + alpha * (reward + gamma * np.max(Q[next_state]))
            # Update returns count for the visited state-action pair
            returns_count[state, action] += 1

            if done:
                break
            state = next_state
    # Calculates average utility for each state-action pair
    average_utilities = Q * returns_count

    return Q, returns_count , average_utilities

def epsilon_greedy_policy(Q, state, epsilon, n_actions):
    if np.random.rand() < epsilon or state not in Q:
        return np.random.choice(n_actions)
    else:
        return np.argmax(Q[state])


def choose_algorithm():
    algorithm = input("Choose the reinforcement learning algorithm (s for SARSA, m for Monte Carlo, q for Q-learning): ").lower()
    return algorithm

def run_chosen_algorithm(algorithm, episodes, slip_probability, grid_size, epsilon):
    if algorithm == 'm':
        for slip_probability in slip_probabilities:
            Q_values, returns_count = monte_carlo_epsilon_greedy(episodes, slip_probability, grid_size, epsilon)
            print(f"\nResults for Slip Probability = {slip_probability} and Epsilon = {epsilon}:\n")

            # Print Q-values for each state-action pair
            for state in Q_values:
               for action, q_value in enumerate(Q_values[state]):
                   print(f"State: {state}, Action: {action}, Q-Value: {q_value}")

            # Calculate and print average utility for each state-action pair
            print("\nAverage Utility:")
            for state in Q_values:
                 for action, q_value in enumerate(Q_values[state]):
                     print(f"State: {state}, Action: {action}, Average Utility: {q_value * returns_count[state][action]}")
            # Calls monte carlo algorithm function
        pass
    elif algorithm == 's':
        for slip_probability in slip_probabilities:
           Q_values ,returns_count = sarsa(episodes, slip_probability, grid_size, epsilon)
           returns_count =1
           print(f"\nResults for Slip Probability = {slip_probability} and Epsilon = {epsilon}:\n")
           for state_int in range(np.prod(grid_size)):
               state = (state_int // grid_size[1], state_int % grid_size[1])
           for action, q_value in enumerate(Q_values.get(state_int, np.zeros(4))):
                print(f"State: {state}, Action: {action}, Q-Value: {q_value}")
           # Q_values, returns_count = monte_carlo_epsilon_greedy(episodes, slip_probability, grid_size, epsilon)
    elif algorithm == 'q':
        # Call Q-learning algorithm function here
        alpha_q_learning = 0.1
        gamma_q_learning = 0.9
        Q_values_q_learning, average_utilities_q_learning, returns_count_q_learning = q_learning_with_average_utility(
             episodes, slip_probability, grid_size, alpha_q_learning,
             gamma_q_learning, epsilon)

       # Print Q-values and average utilities for each state-action pair
        print("\nResults for Q-learning with Average Utility:")
        for state in range(np.prod(grid_size)):
           for action, q_value in enumerate(Q_values_q_learning[state]):
               average_utility = average_utilities_q_learning[state, action]
               print(f"State: {state}, Action: {action}, Q-Value: {q_value}, Average Utility: {average_utility}")
        pass
        # return Q_values,returns_count,average_utility
    else:
        print("Invalid choice. Please choose a valid algorithm.")
        return None

    return 0

# Example usage with epsilon-greedy exploration
episodes = int(input("Enter the number of episodes: "))
slip_probabilities = [float(x) for x in input("Enter slip probabilities (comma-separated): ").split(",")]
grid_size = tuple(map(int, input("Enter grid size (comma-separated, e.g., 4,4): ").split(",")))
epsilon = float(input("Enter epsilon value: "))
algo = choose_algorithm()

if algo:
    run_chosen_algorithm(algo, episodes, slip_probabilities[0], grid_size, epsilon)
