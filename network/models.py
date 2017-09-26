import keras
from keras.models import Sequential, model_from_json
from keras.layers import Dense, Dropout, Activation, Flatten, Input, Reshape
from keras.layers import Convolution1D as Conv1D, MaxPooling1D, Convolution2D as Conv2D, MaxPooling2D
from keras.layers import LSTM, Embedding, SimpleRNN, TimeDistributed
from keras.constraints import maxnorm
from keras.optimizers import SGD, Adam
from keras.models import Model
from keras.utils import np_utils
from keras import backend as K
K.set_image_dim_ordering('tf')


from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error

import numpy as np
from collections import namedtuple

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

__LAYERS__ = {
  
  "lstm": LSTM
}


_network_params = ["code", "n_securities", "price_factors", "fund_factors", \
                   "other_factors", "n_days"]

#NetworkParams = namedtuple("Network Params", code, n_securities, price_factors)

class MarketNN(object):

  def __init__(self, param_dict):

    log.info("initializing network...")

    self.n_securities = param_dict["n_securities"]
    self.price_factors = param_dict["price_factors"]
    self.n_days = 10
    self.lr = param_dict["lr"]
    assert self.n_days > 3, "The pipeline requires at least 5 days worth of data"
    #self.n_portfolio_factors = n_portfolio_factors
    #self.model = self.build_model()


  def build_model(self):

    n_days = self.n_days
    n_securities = self.n_securities
    n_factors = self.price_factors
    log.info("Building model...")
    shape = (n_days, n_securities, n_factors - n_days + 1)
    
    main_market_input = Input(shape = shape)
    conv1 = Conv2D(32, (4,4), activation = "relu", use_bias = True,
      input_shape = shape)(main_market_input)
    conv2 = Conv2D(64, (2,2), activation = "relu", use_bias = True)(conv1)
    conv3 = Conv2D(64, (2,2), activation = "relu", use_bias = True)(conv2)
    pool = MaxPooling2D((3,3))(conv3)
    drop1 = Dropout(.5)(pool)
    flat = Flatten()(drop1)
    dense1 = Dense(128, activation = "relu", use_bias = True,)(flat)


    output = Dense(n_securities * 3, activation = "relu", use_bias = True,)(dense1)

    main_security_input = []
    main_security_output = []
    for i in xrange(n_securities):
      security_input = Input(shape = (1, n_factors))

      conv4 = Conv1D(filters=32, kernel_size=3, padding='same', activation='relu')(security_input)
      #pool2 = MaxPooling1D(pool_size=2)(conv4)
      lstm1 = LSTM(20, activation = "relu", dropout=0.2, 
        recurrent_dropout=0.2, return_sequences = True)(conv4)
      #output2 = Dense(3, activation = "softmax")(lstm1)
      output2 = TimeDistributed(Dense(3, activation = "relu"))(lstm1)

      main_security_input.append(security_input)
      main_security_output.append(output2)

    conf_output = Dense(1, activation = "sigmoid")(output)


    model = Model(inputs = [main_market_input] + main_security_input,
            outputs = [output] + main_security_output + [conf_output])
    sgd = SGD(lr=self.lr, decay=1e5, momentum=0.5, nesterov=True)
    model.compile(optimizer=sgd, loss = 'mse', metrics=['accuracy'])
    return model

  def process_market(self, main_security_input, code = ""):

    n_factors = self.price_factors
    n_days = self.n_days
    n_securities = self.n_securities

    x = Conv2D(32, (1, 1), activation = "sigmoid", 
      input_shape = (n_factors - n_days, n_securities, 1))(main_security_input)

    #x = Conv2D(32, (3, 3), activation='relu')(x)
    #x = MaxPooling2D(pool_size=(4, 4))(x)
    #x = Dropout(0.25)(x)
    x = Flatten()(x)
    x = Dense(16, activation = "relu")(x)   

    return x

  def process_portfolio(self, main_portfolio_input, code):

    x = Dense(2, activation = "relu")(main_portfolio_input)
    return x

  def process_security(self, security_input, market_output):#, portfolio_output):

    n_factors = self.price_factors
    
    #y = Reshape(target_shape = (16, ))(market_output)
    #x = LSTM(20, activation = "relu", input_shape = (1, self.n_factors, ))(security_input)
    x = Reshape(target_shape = (n_factors, ))(security_input)
    x = Dense(50, activation = "sigmoid")(x)
    #x = Dense(16, activation = "relu")(x)
    #x = Flatten()(x)
    x = keras.layers.concatenate([x, market_output])
    
    #x = LSTM(32, activation = "relu")(x)
    #x = Dense(25, activation = "relu")(x)
    #x = Dropout(.2)(x)
    x = Dense(3, activation = "sigmoid")(x)
    return x



  def build_model2(self):

    n_factors = self.price_factors
    n_securities = self.n_securities
    n_days = self.n_days

    main_market_input = Input(shape = (n_days, n_securities, n_factors - n_days))
    #main_portfolio_input = Input(shape = (self.n_portfolio_factors, ))
    main_security_input = []
    market_output = self.process_market(main_market_input)
    #portfolio_output = self.process_portfolio(main_portfolio_input)

    main_security_output = []
    for stock in xrange(n_securities):
      security_input = Input(shape = (1, n_factors, ))
      main_security_input.append(security_input)
      security_output = self.process_security(security_input, market_output)#, portfolio_output)
      main_security_output.append(security_output)

    #aux_confidence_output = Dense(2, activation = "softmax")(market_output)
    model = Model(inputs = [main_market_input] + main_security_input,
            outputs = main_security_output) #+ [aux_confidence_output])
    sgd = SGD(lr=self.lr, decay=1e5, momentum=0.5, nesterov=True)
    model.compile(optimizer=sgd, loss = 'mse', metrics=['accuracy'])
    return model


  def predict_stocks(self, code, n_stocks, output_size = 3):

    network = self.build_network(code)

    for stock in xrange(n_stocks):

      inputs = self.inputs["stocks"][stock]

      stock_prediction = self.predict_stock(network, inputs, n_stocks, output_size)

  def stock_predict(self, network, inputs, n_stocks, output_size = 3):

    output = network.input(nodes)

    predictions = Dense(output_size, activation = "softmax")(output)
    stock_predictions.append(predictions)

    return stock_predictions 



