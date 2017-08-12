import numpy as np
import random
from util import Positions
from collections import deque
from keras.models import Sequential, model_from_json
from keras.layers import Dense, Activation
from keras.optimizers import SGD, Adam
"""
100 X 2

"""

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def action_values_to_trades(actions):

	x = 3
	n_securities = len(actions) / 3

	trades = []

	for i in xrange(n_securities):

		trades.append(np.argmax(actions[3*i:3*i + 3]) - 1)
	return trades

#def evaluate_future_returns(q):



class DQNAgent(object):

	def __init__(self, state_size, action_size):

		self.state_size = state_size
		self.action_size = action_size
		self.memory = deque(maxlen = 2000)
		self.gamma = .95 # discount rate
		self.epsilon = 1.0 # exploration rate
		self.epsilon_min = .01
		self.epsilon_decay = .995
		self.learning_rate = .001
		self.batch_size = 32
		self.space = Positions(self.state_size)
		self.model = self._build_model()

	def _build_model(self):

		model = Sequential()
		model.add(Dense(24, input_dim = self.state_size, activation = 'relu'))
		model.add(Dense(24, activation='relu'))
		model.add(Dense(self.action_size, activation='linear'))
		model.compile(loss='mse', optimizer=Adam(lr=self.learning_rate))
		return model

	def save(self, name):

		path = "models/"

		# serialize model to JSON
		model_json = self.model.to_json()
		with open(path + name + ".json", "w") as json_file:
			json_file.write(model_json)
			# serialize weights to HDF5
			self.model.save_weights(path + name + ".h5")
			logger.info("Saved model to disk: " + name + "\n")

	def load(self, name):

		path = "models/"

		# load json and create model
		json_file = open(path + name + ".json", 'r')
		loaded_model_json = json_file.read()
		json_file.close()
		loaded_model = model_from_json(loaded_model_json)
		# load weights into new model
		loaded_model.load_weights(path + name + ".h5")
		self.model = loaded_model
		self.model.compile(loss='mse', optimizer=Adam(lr=self.learning_rate))
		self.epsilon = .5
		logger.info("Loaded model (" + name + ") from disk")

	def remember(self, state, action, reward, next_state, done):

		self.memory.append((state, action, reward, next_state, done))

	def act(self, state):

		if np.random.rand() <= self.epsilon:
			return self.space.sample()
		else:
			state = np.reshape(state.values, [1, self.state_size])
			action_values = self.model.predict(state)
			return action_values_to_trades(action_values[0])

	def replay(self):

		minibatch = random.sample(self.memory, self.batch_size)
		for state, action, reward, next_state, done in minibatch:


			state = np.reshape(state.values, [1, self.state_size])
			next_state = np.reshape(next_state.values, [1, self.state_size])

			target = reward
			if not done:
				target = reward + self.gamma * np.amax(self.model.predict(next_state)[0])

			target_f = self.model.predict(state)

			actions = action_values_to_trades(target_f[0])

			for i in xrange(len(actions)):
				action = actions[i]
				node = 3*i + (action + 1)
				target_f[0][node] = target #/ float(len(actions))


			target_f[0][np.random.randint(0, self.action_size)] = target

			self.model.fit(state, target_f, epochs = 1, verbose = 0)

		if self.epsilon > self.epsilon_min:
			self.epsilon *= self.epsilon_decay
