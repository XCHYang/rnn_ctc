import theano.tensor as tt
import theano as th
from theano.tensor.nnet import sigmoid
import numpy as np
from activations import share, activation_by_name


def orthonormal_wts(n, m):
    nm = max(n, m)
    return np.linalg.svd(np.random.randn(nm, nm))[0].astype(
        th.config.floatX)[:n, :m]


def stacked_wts(n, m, copies, name=None):
    return share(
        np.hstack([orthonormal_wts(n, m) for _ in range(copies)]),
        name=name)


class LSTM():
    """
    Long Short Term Memory Layer.
    Does not implement incell connections from cell value to the gates.
    Reference: Supervised Sequence Learning with RNNs by Alex Graves
                Chapter 4, Fig 4.2
    """
    def __init__(self, inpt,
                 nin, nunits,
                 forget=False,
                 actvn_pre='tanh',
                 actvn_post='linear'):
        """
        Init
        :param inpt: Lower layer's excitation.
        :param nin: Dimension of lower layer.
        :param nunits: Number of units.
        :param forget: Want a seperate forget gate (or use 1-input).
        :param actvn_pre: Activation applied to new candidate for cell value.
        :param actvn_post: Activation applied to cell value before output.
        :return: Output
        """
        # TODO: Incell connections
        # TODO: Initial states as parameters

        num_activations = 3 + forget
        w = stacked_wts(nin, nunits, num_activations)
        u = stacked_wts(nunits, nunits, num_activations)
        b = share(np.zeros((num_activations * nunits)))

        actvn_pre = activation_by_name(actvn_pre)
        actvn_post = activation_by_name(actvn_post)

        def step(in_t, out_tm1, cell_tm1):
            """
            Scan function.
            :param in_t: Current input from bottom layer
            :param out_tm1: Prev output of LSTM layer
            :param cell_tm1: Prev cell value
            :return: Current output and cell value
            """
            tmp = tt.dot(out_tm1, u) + in_t

            inn_gate = sigmoid(tmp[:nunits])
            out_gate = sigmoid(tmp[nunits:2*nunits])
            fgt_gate = sigmoid(tmp[2*nunits:3*nunits]) if forget else 1-inn_gate

            candidate = actvn_pre(tmp[-nunits:])
            cell_val = fgt_gate * cell_tm1 + inn_gate * candidate
            out = out_gate * actvn_post(cell_val)

            return out, candidate

        inpt = tt.dot(inpt, w) + b
        # seqlen x nin * nin x 3*nout + 3 * nout  = seqlen x 3*nout

        rval, updates = th.scan(step,
                                sequences=[inpt],
                                outputs_info=[np.zeros(nunits),
                                              np.zeros(nunits)],)

        self.output = rval[0]
        self.params = [w, u, b]
        self.nout = nunits