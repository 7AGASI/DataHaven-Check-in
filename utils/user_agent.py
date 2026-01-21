import random

def get_user_agent():
    user_agents = []

    with open('utils/user-agents.txt', 'r') as f:
        for line in f:
            line = line.strip()

            user_agents.append(line)

    return random.choice(user_agents)

