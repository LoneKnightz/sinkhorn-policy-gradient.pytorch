# Generate sorting data and store in .txt
# Define the reward function 

import torch
import math
from torch.utils.data import Dataset
from torch.autograd import Variable
from tqdm import trange, tqdm
import os
import sys
import numpy as np
from sklearn.utils.linear_assignment_ import linear_assignment

def reward(matching, use_cuda):
    """
    matching is Tensor of dim [batch, N, 2]
    """
    (batch_size, N, features) = matching.size()
    matching_weight = Variable(torch.zeros(batch_size, 1), requires_grad=False)
    if use_cuda:
       matching_weight = matching_weight.cuda()
    M = int(N/2)    
    for i in range(M):
        dists = torch.norm(matching[:, i + M, :] - matching[:, i, :], 2, dim=1)
        matching_weight += dists.float()
    return matching_weight 
def reward_nco(matching, use_cuda):
    """
    matching is a list of N Tensors of dim [batch, 4]
    """
    #return -reward(torch.stack(matching, 1), use_cuda)
    return -reward(matching, use_cuda)

def create_dataset(
        train_size,
        val_size,
        test_size,
        data_dir,
        N,
        random_seed=None,
        sl=False,
        only=-1):    
    # only == 0, only train
    # only == 1, only val
    # only == 2, only test
    # only == -1, all
    # only == 3, none

    if random_seed is not None:
        torch.manual_seed(int(random_seed))

    train_dir = os.path.join(data_dir, 'train', 'N={}'.format(N))
    val_dir = os.path.join(data_dir, 'val', 'N={}'.format(N))
    test_dir = os.path.join(data_dir, 'test', 'N={}'.format(N))
    if only == 3:
        return train_dir, val_dir, test_dir
    
    if not os.path.isdir(train_dir):
        os.mkdir(train_dir)
    if not os.path.isdir(val_dir):
        os.mkdir(val_dir)
    if not os.path.isdir(test_dir):
        os.mkdir(test_dir)

    
    def to_string(tensor, label=None):
        """
        Convert a torch.FloatTensor 
        of size 2xN
        """
        if label is not None:
            matching, weight = label
        mat = ''
        for ii in range(4):
            for jj in range(N-1):
                mat += '{} '.format(tensor[ii, jj])
            if ii < 3 or label is None:
                mat += '{}'.format(tensor[ii,-1]) + '\n'
            else:
                mat += '{} '.format(tensor[ii,-1])
                for k in range(N):
                    mat += '{} '.format(matching[k])
                mat += '{}'.format(weight) + '\n'
        return mat
    # Generate a training set of size train_size
    ctr = 0
    for idx in trange(train_size + val_size + test_size):
        x = torch.FloatTensor(4, N).uniform_(0, 1)
        if sl or idx > train_size:
            # x is a (N, 2, 2)
            x_ = x.numpy()
            # compute reward matrix C to maximize
            C = np.zeros((N,N))
            for i in range(N):
                for j in range(N):
                    C[i,j] = np.linalg.norm(x_[2:4, i] - x_[0:2, j], ord=2)
            # Find the max matching
            max_matching = linear_assignment(-C)
            weight = np.sum(C[max_matching[:,0], max_matching[:,1]])                
            if idx < train_size and (only == -1 or only == 0):
                sample = to_string(x, (max_matching[:,1], weight))
                fp = open(os.path.join(train_dir, '{}.txt'.format(ctr)), 'w')
                fp.write(sample)
                fp.close()
            elif idx < train_size + val_size and (only == -1 or only == 1):
                sample = to_string(x, (max_matching[:,1], weight))
                fp = open(os.path.join(val_dir, '{}.txt'.format(ctr - train_size)), 'w')
                fp.write(sample)
                fp.close()               
            elif idx < train_size + val_size + test_size and (only == -1 or only == 2):
                sample = to_string(x, (max_matching[:,1], weight))
                fp = open(os.path.join(test_dir, '{}.txt'.format(ctr - (train_size + val_size))), 'w')
                fp.write(sample)
                fp.close()
        else:
            sample = to_string(x)
            fp = open(os.path.join(train_dir, '{}.txt'.format(ctr)), 'w')
            fp.write(sample)
            fp.close()
        ctr += 1
    return train_dir, val_dir, test_dir

class MWM2DDataset(Dataset):

    def __init__(self, data_dir, size, has_labels=False):
        super(MWM2DDataset, self).__init__()
        self.has_labels = has_labels
        self.data_dir = data_dir
        self.size = size

    def __len__(self):
        return self.size

    def __getitem__(self, idx):
        with open(os.path.join(self.data_dir, '{}.txt'.format(idx)), 'r') as dset:
            lines = dset.readlines()
            N = len(lines[0].split())
            graph = torch.zeros(2*N, 2)
            matching = torch.zeros(N)       
            labels = []     
            for ctr, next_line in enumerate(lines):
                toks = next_line.split() 
                for ii, tok in enumerate(toks):
                    if ii < N and ctr < N:
                        graph[(int(ctr / 2) * N) + ii, ctr % 2] = float(tok)
                    elif self.has_labels and ii < 2 * N:
                        matching[int(ii % N)] = float(tok)
                    elif self.has_labels:
                        labels.append((matching, float(tok)))
        if self.has_labels:
            return {'x': graph, 'matching': labels[0][0], 'weight': labels[0][1]}
        else:
            return {'x': graph}

if __name__ == '__main__':
    sizes = [5, 10, 15, 20, 25]
    for i in sizes:
        create_dataset(0, 0, 10000, '/home/pemami/Workspace/deep-assign/data/mwm2D/icml2018', i, 3, True, 2)
    """
    import time
    from torch.utils.data import DataLoader

    sizes = [5, 10, 15, 20, 25]
    ds = ['val']
    ee = [100000]
    for sz in sizes:
        for d, e in zip(ds, ee):
            #N = int(sys.argv[1])
            data_dir = '/home/pemami/Workspace/deep-assign/data/mwm2D/icml2018'
            #train_fn, val_fn, test_fn = create_dataset(500000, 100000, 10000, data_dir, N=N, epoch=0, reset=False, random_seed=3, sl=True)
            fn = os.path.join(data_dir, 'max-weight-matching-2D-size-{}-N-{}-{}.txt'.format(e, sz, d))
            dataset = os.path.join(data_dir, fn)
            has_labels = True
            #mwm_data = MWM2DDataset(data_dir, 500000, has_labels=True)
            
            # print(mwm_data[100])
            # start = time.time()
            # print(mwm_data[1000])
            # diff = time.time() - start
            # print("took {} to retrieve one sample".format(diff))

            # train_dataloader = DataLoader(mwm_data, batch_size=128, shuffle=True, num_workers=4)
            # for idx, batch in tqdm(enumerate(train_dataloader)):
            #     pass

            ctr = 0  
            target_dir = os.path.join(data_dir, d, 'N={}'.format(sz))
            if not os.path.isdir(target_dir):
                os.mkdir(target_dir)
            count = 0  
            target_fname = os.path.join(target_dir, '{}.txt'.format(count))
            target_fp = open(target_fname, 'w')
            with open(dataset, 'r') as fp:
                for i, line in enumerate(fp): 
                    if ctr < 4:
                        target_fp.write(line)                             
                    else:
                        ctr = 0
                        count += 1
                        target_fname = os.path.join(target_dir, '{}.txt'.format(count))
                        target_fp.close()
                        target_fp = open(target_fname, 'w')
                        target_fp.write(line) 
                    ctr += 1                            
            target_fp.close()
    """