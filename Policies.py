import tensorflow as tf
from tensorflow.keras import layers, Model, Input, Sequential
import tensorflow_probability as tfp



def mlp_net_boltzmann(input_shape, n_outputs):
    
    inputs = Input(shape = input_shape)

    hidden_layers = [layers.Dense(64, activation = tf.nn.relu, name = "hidden_layers")]
    h_inputs = inputs
    for h_layer in hidden_layers:
        h_inputs = h_layer(h_inputs)
    
    policy_layers = [layers.Dense(256, activation = tf.nn.relu, name = "policy_layers")]
    p_inputs = h_inputs
    for p_layer in policy_layers:
        p_inputs = p_layer(p_inputs)

    value_layers = [layers.Dense(128, activation = tf.nn.relu, name = "value_layers")]
    v_inputs = h_inputs
    for v_layer in value_layers:
        v_inputs = v_layer(v_inputs)
    
    policy_head = layers.Dense(n_outputs, activation = tf.nn.softmax, name = "policy_head")(p_inputs) 
    value_head = layers.Dense(1, activation = tf.nn.tanh, name = "value_head")(v_inputs)
    model = Model(inputs = [inputs], outputs = [policy_head, value_head])

    return model

def mlp_net_gaussian(input_shape, n_outputs):

    inputs = Input(shape = input_shape)

    hidden_layers = [layers.Dense(64, activation = tf.nn.relu, name = "hidden_layers")]
    h_inputs = inputs
    for h_layer in hidden_layers:
        h_inputs = h_layer(h_inputs)
    
    policy_layers = [layers.Dense(128, activation = tf.nn.relu, name = "policy_layers")]
    p_inputs = h_inputs
    for p_layer in policy_layers:
        p_inputs = p_layer(p_inputs)

    value_layers = [layers.Dense(128, activation = tf.nn.relu, name = "value_layers")]
    v_inputs = h_inputs
    for v_layer in value_layers:
        v_inputs = v_layer(v_inputs)
    
    mean = layers.Dense(1, activation = tf.nn.softmax, name = "mean")(p_inputs) 
    std = layers.Dense(1, activation = tf.nn.softmax, name = "std")(p_inputs)
    value_head = layers.Dense(1, activation = tf.nn.tanh, name = "value_head")(v_inputs)
    model = Model(inputs = [inputs], outputs = [mean, std, value_head])

    return model


class CSerializable:

    def __init__(self, path):
        self.__path = path

    def _save(self, model):
        if self.__path is not None:
            tf.keras.models.save_model(model, self.__path)

    def load(self):
        return tf.keras.models.load_model(self.__path)
    
    def get_path(self):
        return self.__path


class Policy(CSerializable):
    def __init__(self, input_shape, n_outputs, net = None, model_path=None):
        
        self.input_shape = input_shape
        self.n_outputs = n_outputs
        self.model_path = model_path
        super(Policy, self).__init__(self.model_path)
        self._net = self._get_net(net = net, model_path = model_path)
        self.trainable_variables = self._net.trainable_variables
    
    def _get_net(self, net = None, model_path= None):

        if net == None and model_path == None:
            raise "Function approximator isn't passed"
        network = None
        if model_path is None:
            network = net(self.input_shape, self.n_outputs)
        else:
            try:
                network = self.load()
                print("Loaded from path")
            except OSError:
                print("Using default net...")
                network = net(self.input_shape, self.n_outputs)
        return network
        
        
    #Override this
    def __call__(self, state):
        pass
    
    def get_net(self):
        return self._net
    
    def get_architecture(self):
        self._net.summary()
        return tf.keras.utils.plot_model(self._net, "net.png", show_shapes=True)
    
    def save(self):
        if self.model_path is not None:
            self._save(self._net)


class BoltzmannPolicy(Policy):
    def __init__(self, state_spec, action_spec, net = None, model_path=None):

        self.state_spec = state_spec
        self.action_spec = action_spec
        super(BoltzmannPolicy, self).__init__(state_spec.shape, action_spec.n, 
                                              net = net, model_path= model_path)

    def __call__(self, state):
        if state.shape == self.state_spec.shape:
            state = tf.reshape(state, shape = [-1,*state.shape])
        probs, value = self._net(state)
        dist = tfp.distributions.Categorical(probs = probs)
        return dist.sample(), dist, value

class GaussianPolicy(Policy):
    def __init__(self, state_spec, action_spec, net = None, model_path=None):
        self.state_spec = state_spec
        self.action_spec = action_spec
        super(GaussianPolicy, self).__init__(state_spec.shape, 1, 
                                            net = net, model_path= model_path)

    def __call__(self, state):
        if state.shape == self.input_shape:
            state = tf.reshape(state, shape = [-1,*state.shape])
        mean, std, value = self._net(state)
        dist = tfp.distributions.Normal(mean, std)
        action = tf.clip_by_value(dist.sample(), env.action_space.low,env.action_space.high)
        return action, dist, value


def make_policy(state_spec, action_spec, save_path = None):
    
    if isinstance(action_spec, gym.spaces.Discrete):
        
        return BoltzmannPolicy(state_spec, action_spec, net = mlp_net_boltzmann,
                               model_path = save_path)

    elif isinstance(action_spec, gym.spaces.Box):
        return GaussianPolicy(state_spec, action_spec, net = mlp_net_gaussian,
                             model_path = save_path)




