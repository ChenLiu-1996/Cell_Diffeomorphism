import cv2
import numpy as np
import skimage.feature
import skimage.segmentation


def detect_nuclei(img: np.array, return_overlay: bool = False):
    if img.shape[-1] == 1:
        # (H, W, 1) to (H, W, 3)
        img = np.repeat(img, 3, axis=-1)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Pad white the image to avoid border effects
    gray = cv2.copyMakeBorder(gray, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=[255, 255, 255])

    # Setup SimpleBlobDetector parameters.
    print('Default parameters: =====')
    params = cv2.SimpleBlobDetector_Params()
    for p in dir(params):
        if not p.startswith('__'):
            print(p, getattr(params, p))

    params.minThreshold = 5
    params.maxThreshold = 220

    # params.filterByArea = True
    params.minArea = 150
    params.maxArea = 10000.0

    # params.filterByCircularity = False
    # params.filterByConvexity = False
    # params.filterByInertia = False
    params.minConvexity = 0.8 #0.9499
    params.minDistBetweenBlobs = 1

    # # Create a detector with the parameters
    # detector = cv2.SimpleBlobDetector_create(params)
    print('Updated parameters: =====')
    for p in dir(params):
        if not p.startswith('__'):
            print(p, getattr(params, p))
    detector = cv2.SimpleBlobDetector_create(params)

    # Detect blobs.
    keypoints = detector.detect(gray)

    nuclei_list = []
    for kp in keypoints:
        (w, h) = kp.pt
        nuclei_list.append([h, w])

    if return_overlay:
        # Draw detected blobs as red circles.
        # cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS ensures the size of the circle corresponds to the size of blob
        im_with_keypoints = cv2.drawKeypoints(gray, keypoints, np.array([]), (0, 0, 255),
                                              cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
        return nuclei_list, im_with_keypoints
    else:
        return nuclei_list

def detection_eval(nuclei_list, mask, total_pos):
    # Convert nuclei_list to mask
    mask = (mask > 0) * 1.0
    nuclei_mask = np.zeros_like(mask)
    #print(nuclei_list)
    for n in nuclei_list:
        if n[0] < 0 or n[0] >= mask.shape[0] or n[1] < 0 or n[1] >= mask.shape[1]:
            continue
        nuclei_mask[int(n[0]), int(n[1])] = 1

    # Compute accuracy
    TP = np.sum(nuclei_mask * mask)
    FN = total_pos - TP
    # TN = np.sum((1 - nuclei_mask) * (1 - mask))

    # accuracy = (TP + TN) / (TP + TN + FP + FN)
    recall = TP / (TP + FN)
    # f1 = 2 * precision * recall / (precision + recall)
    return recall, TP, FN


import os
from glob import glob
from Metas import Organ2FileID
from matplotlib import pyplot as plt

if __name__ == '__main__':
    organ = 'Breast'
    print('Organ:', organ)
    file_ids = Organ2FileID[organ]['test']

    img_path_list = [f'../../external_data/MoNuSeg/MoNuSegTestData/images/{file_id}.png' for file_id in file_ids]
    mask_path_list = [f'../../external_data/MoNuSeg/MoNuSegTestData/masks/{file_id}.png' for file_id in file_ids]
    image_list = [cv2.cvtColor(cv2.imread(image_path, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB) for image_path in img_path_list]
    mask_list = [cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE) for mask_path in mask_path_list]

    test_patch_folder = os.path.join('/gpfs/gibbs/pi/krishnaswamy_smita/dl2282/CellSeg/data/MoNuSeg2018TestData_patch_32x32', 'label')
    test_patch_files = sorted(glob(os.path.join(test_patch_folder, '*.png')))

    n = len(image_list)

    fig = plt.figure(figsize=(18, 6*n))
    for i in range(n):
        image = image_list[i]
        mask = mask_list[i]

        ax = fig.add_subplot(n, 3, 3*i+1)
        ax.imshow(image)
        ax.set_axis_off()

        # Detected nuclei
        ax = fig.add_subplot(n, 3, 3*i+2)
        nuclei_list, pseudomask = detect_nuclei(image, return_overlay=True)
        print(f'Detected {len(nuclei_list)} nuclei.')
        ax.imshow(pseudomask, cmap='gray')
        ax.set_axis_off()
        ax.set_title(f'Detected {len(nuclei_list)} nuclei.')

        # Groud truth mask
        filtered_patch_files = [x for x in test_patch_files if f'{file_ids[i]}' in x]
        print(f'Ground truth nuclei count: {len(filtered_patch_files)}')
        ax = fig.add_subplot(n, 3, 3*i+3)
        ax.imshow(mask, cmap='gray')
        ax.set_axis_off()
        ax.set_title(f'GT nuclei: {len(filtered_patch_files)}')

        # Compute accuracy of detected nuclei
        recall, TP, FN = detection_eval(nuclei_list, mask, total_pos=len(filtered_patch_files))
        print(f'Dection Recall: {recall:.2f}')
        print(f'True Positive: {TP}, False Negative: {FN}')


    fig.savefig('check_nuclei_detector.png')