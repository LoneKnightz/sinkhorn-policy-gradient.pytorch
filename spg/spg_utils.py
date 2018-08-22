import numpy as np
from math import log10, floor
import torch
from scipy.stats import entropy
#from sklearn.utils.linear_assignment_ import linear_assignment as munkres
import spg.linear_assignment as linear_assignment

def str2bool(v):
      return v.lower() in ('true', '1')

def logsumexp(inputs, dim=None, keepdim=False):
    """Numerically stable logsumexp.

    Args:
        inputs: A Variable with any shape.
        dim: An integer.
        keepdim: A boolean.

    Returns:
        Equivalent of log(sum(exp(inputs), dim=dim, keepdim=keepdim)).
    """
    # For a 1-D array x (any array along a single dimension),
    # log sum exp(x) = s + log sum exp(x - s)
    # with s = max(x) being a common choice.
    if dim is None:
        inputs = inputs.view(-1)
        dim = 0
    s, _ = torch.max(inputs, dim=dim, keepdim=True)
    outputs = s + (inputs - s).exp().sum(dim=dim, keepdim=True).log()
    if not keepdim:
        outputs = outputs.squeeze(dim)
    return outputs

def matching(batch):
    perms = []
    (m, n, n) = batch.shape
    for i in range(m):
        perm = torch.zeros(n, n)
        matching = linear_assignment.linear_assignment(-batch[i].astype(np.float64))
        perms.append(torch.from_numpy(np.asarray(matching)).float())
    return perms

def memory_usage():
    return ((int(open('/proc/self/statm').read().split()[1]) * 4096.) / 1000000.)

def birkhoff_distance(soft_perm, hard_perm):
    n_nodes = soft_perm.size()[1]
    return torch.sum(torch.sum(soft_perm * hard_perm, dim=1), dim=1) / n_nodes

def permute_sequence(sequence, permutation):
    return torch.matmul(torch.transpose(sequence, 1, 2), permutation)

def permute_bipartite(bipartite, permutation):
    n_nodes = int(bipartite.size()[1]/2)
    matching = torch.matmul(torch.transpose(bipartite[:, n_nodes:2*n_nodes, :], 1, 2),
            permutation)
    matching = torch.transpose(matching, 1, 2)
    matching = torch.cat([bipartite[:, 0 : n_nodes, :], matching], dim=1)
    return matching

def k_exchange(k, soft_perm, hard_perm):
    n_nodes = soft_perm.size()[1]
    for r in range(k):
        idxs = np.random.randint(0, n_nodes, size=2)
        # swap the two rows
        tmp = hard_perm[:, idxs[0]].clone()
        tmp2 = hard_perm[:, idxs[1]].clone()
        tmp3 = soft_perm[:, idxs[0]].clone()
        tmp4 = soft_perm[:, idxs[1]].clone()
        hard_perm[:, idxs[0]] = tmp2
        hard_perm[:, idxs[1]] = tmp
        soft_perm[:, idxs[0]] = tmp4
        soft_perm[:, idxs[1]] = tmp3
    return soft_perm, hard_perm

def kullback_leibler(p, q):
    """
    Computes the KL divergence averaged over a minibatch between
    doubly stochastic matrices p and q
    
    Args:
        p: [bsz,n,n] torch FloatTensor (on cpu)
        q: [bsz,n,n] torch FloatTensor (on cpu)
    Returns:
        float, the KL div
    """
    bsz = p.size()[0]
    # We can vectorize the computation
    p = p.view(bsz, -1)
    q = q.view(bsz, -1)
    return torch.sum(p * torch.log(p) - p * torch.log(q), dim=1).mean()

def entropy(p, q):
    """ 
    Average entropy of q wrt p, each [bsz,n,n] tensors
    Avergaed over minibatch

    - sum p * log q
    """
    return -torch.sum(p * torch.log(q), dim=1).mean()
