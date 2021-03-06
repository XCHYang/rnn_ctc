import pickle
import sys
import numpy as np
import theano as th

from configurations import configs
from neuralnet import NeuralNet
from print_utils import slab_print, prediction_printer


def show_all(shown_seq, shown_img,
             seen_probabilities=None,
             aux_img=None, aux_name=None):
    """
    Utility function to show the input and output and debug
    :param shown_seq: Labelings of the input
    :param shown_img: Input Image
    :param seen_probabilities: Seen Probabilities (Excitations of Softmax)
    :param aux_img: Other image/matrix for debugging
    :param aux_name: Name of aux
    :return:
    """
    print('Shown : ', end='')
    labels_print(shown_seq)

    if seen_probabilities is not None:
        print('Seen  : ', end='')
        maxes = np.argmax(seen_probabilities, 0)
        labels_print(maxes)

    print('Image Shown:')
    slab_print(shown_img)

    if seen_probabilities is not None:
        print('Firings:')
        slab_print(seen_probabilities)

    if aux_img is not None:
        print(aux_name)
        slab_print(aux_img)

# ################################## Main Script ###########################
config_num = 0

if len(sys.argv) < 2:
    print('Usage\n{} <data_file.pkl> configuration#={}'
          ''.format(sys.argv[0], config_num))
    sys.exit(1)

with open(sys.argv[1], "rb") as pkl_file:
    data = pickle.load(pkl_file)

if len(sys.argv) > 2:
    config_num = int(sys.argv[2])


################################
# Network Parameters

midlayer, midlayerargs = configs[config_num]
nClasses = data['nChars']
nDims = len(data['x'][0])
nSamples = len(data['x'])
nTrainSamples = nSamples * .75
nEpochs = 100
labels_print, labels_len = prediction_printer(nClasses)

print("\nConfig {}"
      "\n\tMidlayer: {} {}"
      "\nInput Dim: {}"
      "\nNum Classes: {}"
      "\nNum Samples: {}"
      "\n".format(config_num, midlayer, midlayerargs,
                  nDims, nClasses, nSamples))

################################
print("Preparing the Data")
try:
    conv_sz = midlayerargs["conv_sz"]
except KeyError:
    conv_sz = 1

data_x, data_y = [], []
bad_data = False

for x, y in zip(data['x'], data['y']):
    # Insert blanks at alternate locations in the labelling (blank is nClasses)
    y1 = [nClasses]
    for char in y:
        y1 += [char, nClasses]

    data_y.append(np.asarray(y1, dtype=np.int32))
    data_x.append(np.asarray(x, dtype=th.config.floatX))

    if labels_len(y1) > (1 + len(x[0])) // conv_sz:
        bad_data = True
        show_all(y1, x, None, x[:, ::conv_sz], "Squissed")


################################
print("Building the Network")

ntwk = NeuralNet(nDims, nClasses, midlayer, midlayerargs)

print("Training the Network")
for epoch in range(nEpochs):
    print('Epoch : ', epoch)
    for samp in range(nSamples):
        x = data_x[samp]
        y = data_y[samp]

        if samp < nTrainSamples:
            cst, pred, aux = ntwk.trainer(x, y)
            if (epoch % 10 == 0 and samp < 3) or np.isinf(cst):
                print('## TRAIN cost: ', np.round(cst, 3))
                show_all(y, x, pred, aux > 0, 'Forward probabilities:')
            if np.isinf(cst):
                print(
                    'Exiting on account of Inf Cost on the following data...')
                sys.exit()

        elif (epoch % 10 == 0 and samp - nTrainSamples < 3) \
                or epoch == nEpochs - 1:
            # Print some test images
            pred, aux = ntwk.tester(x)
            aux = (aux + 1) / 2.0
            print('## TEST')
            show_all(y, x, pred, aux, 'Convolution:')