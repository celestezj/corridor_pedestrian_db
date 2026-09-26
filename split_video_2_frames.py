import cv2
import os.path as osp
import os, shutil

num = 0   # 帧计数器
del_cnt = 0
gen_cnt = 0
img_suffix = {".jpg", ".jpeg", ".png", ".bmp", ".JPG", ".PNG"} # 支持删除的图片后缀
_sample_interval = 1
images_dir = None

def split_one_video(video_path):
    global num, gen_cnt, img_suffix, _sample_interval, images_dir
    video_path = osp.abspath(video_path)
    save_step = _sample_interval   # 采样间隔帧
    video = cv2.VideoCapture(video_path)

    if not video:
        print(f"Error: can not open video file '{video_path}'")
    while True:
        ret, frame = video.read()
        if not ret:
            break
        if (num % save_step == 0):
            cv2.imwrite(osp.normpath(osp.join(images_dir, f'{num}.jpg')), frame)
            gen_cnt += 1
        num += 1
    print(f'split {video_path} into {images_dir} success, total {gen_cnt} images')

def main(videos_dir, images_save_dir, sample_interval=20):
    global images_dir, _sample_interval, del_cnt, num, gen_cnt, img_suffix
    images_dir = osp.abspath(images_save_dir)
    _sample_interval = sample_interval

    if not osp.exists(videos_dir):
        print(f'Error: {videos_dir} not exist!')
        return
    if not osp.exists(images_dir):
        os.makedirs(images_dir)
        print(f"create {images_dir}")
    else:
        # 遍历删除目录下所有文件
        for file in os.listdir(images_dir):
            file_path = osp.join(images_dir, file)
            # 只删除文件，不删除子文件夹
            if osp.isfile(file_path):
                ext = osp.splitext(file)[1]
                if ext in img_suffix:
                    os.remove(file_path)
                    del_cnt += 1
        print(f"cleared {del_cnt} old images in {images_dir}")
    for eachFile in os.listdir(videos_dir):
        each_filePath = os.path.join(videos_dir, eachFile)
        if osp.isfile(each_filePath):
            ext = osp.splitext(each_filePath)[1]
            if ext in img_suffix:
                dest_filename = os.path.join(images_dir, f'{num}{ext}')
                print(f'copy {each_filePath} to {dest_filename}')
                shutil.copy2(each_filePath, dest_filename)
                num += 1
                gen_cnt += 1
            elif ext in ['.mp4']:
                split_one_video(each_filePath)

if __name__ == '__main__':
    num = 211002 #起始图像帧名
    main('./raw_material', './frames', sample_interval=18)