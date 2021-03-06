from __future__ import division
import argparse
import scipy.misc
import numpy as np
from glob import glob
from joblib import Parallel, delayed
import os

parser = argparse.ArgumentParser()
parser.add_argument("--dataset_dir", type=str, required=True, help="where the dataset is stored")
parser.add_argument("--dump_root", type=str, required=True, help="Where to dump the data")
parser.add_argument("--seq_length", type=int, required=True, help="Length of each training sequence")
parser.add_argument("--img_height", type=int, default=128, help="image height")
parser.add_argument("--img_width", type=int, default=416, help="image width")
parser.add_argument("--num_threads", type=int, default=4, help="number of threads to use")
args = parser.parse_args()

def concat_image_seq(seq):
    res = None
    for i, im in enumerate(seq):
        if i == 0:
            res = im
        else:
            res = np.hstack((res, im))
    return res

def dump_example(n, args):
    if n % 2000 == 0:
        print('Progress %d/%d....' % (n, data_loader.num_train))
    example = data_loader.get_train_example_with_idx(n)
    if example == False:
        return
    if example['image_seq'] is None:
        print(example['file_name'])
        raise Exception
    image_seq = concat_image_seq(example['image_seq'])
    dump_dir = os.path.join(args.dump_root, example['folder_name'])
    # if not os.path.isdir(dump_dir):
    #     os.makedirs(dump_dir, exist_ok=True)
    try: 
        os.makedirs(dump_dir)
    except OSError:
        if not os.path.isdir(dump_dir):
            raise
    dump_img_file = dump_dir + '/%s.jpg' % example['file_name']
    try:
        scipy.misc.imsave(dump_img_file, image_seq.astype(np.uint8))
        print(dump_img_file, "saved!")
    except Exception as E:
        print("There is no", dump_img_file)
        print(E)

def main():
    if not os.path.exists(args.dump_root):
        os.makedirs(args.dump_root)

    global data_loader
    from kitti_gt_loader import kitti_gt_loader
    data_loader = kitti_gt_loader(args.dataset_dir,
                                    split='eigen',
                                    img_height=args.img_height,
                                    img_width=args.img_width,
                                    seq_length=args.seq_length)

    Parallel(n_jobs=args.num_threads)(delayed(dump_example)(n, args) for n in range(data_loader.num_train))

    

    # Split into train/val
    
    # subfolders = os.listdir(args.dump_root)
    # with open(args.dump_root + 'train.txt', 'w') as tf:
    #     with open(args.dump_root + 'val.txt', 'w') as vf:
    #         for s in subfolders:
    #             if not os.path.isdir(args.dump_root + '/%s' % s):
    #                 continue
    #             imfiles = glob(os.path.join(args.dump_root, s, '*.jpg'))
    #             frame_ids = [os.path.basename(fi).split('.')[0] for fi in imfiles]
    #             for frame in frame_ids:
    #                 if np.random.random() < 0.1:
    #                     vf.write('%s %s\n' % (s, frame))
    #                 else:
    #                     tf.write('%s %s\n' % (s, frame)) 깔깔!ㅉㅉ
main()

