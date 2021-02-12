'''
基于FLANN的匹配器(FLANN based Matcher)
1.FLANN代表近似最近邻居的快速库。它代表一组经过优化的算法，用于大数据集中的快速最近邻搜索以及高维特征。
2.对于大型数据集，它的工作速度比BFMatcher快。
3.需要传递两个字典来指定要使用的算法及其相关参数等
对于SIFT或SURF等算法，可以用以下方法：
index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
对于ORB，可以使用以下参数：
index_params= dict(algorithm = FLANN_INDEX_LSH,
                   table_number = 6, # 12   这个参数是searchParam,指定了索引中的树应该递归遍历的次数。值越高精度越高
                   key_size = 12,     # 20
                   multi_probe_level = 1) #2
'''
import cv2
import numpy as np
import datetime
def knnMatcher(originImg,template,debug=False):
    if debug:
        # 初始化计时器
        startTime = datetime.datetime.now()

    # # 初始化SIFT检测器
    # sift = cv2.SIFT_create()
    # # 用SIFT找到关键点和描述符
    # kp1, des1 = sift.detectAndCompute(img1, None)
    # kp2, des2 = sift.detectAndCompute(img2, None)

    # 初始化ORB检测器(Fastest)
    orb = cv2.ORB_create()
    kp1,des1 = orb.detectAndCompute(originImg,None)
    kp2,des2 = orb.detectAndCompute(template,None)
 
    # FLANN参数
    FLANN_INDEX_KDTREE = 0
    FLANN_INDEX_LSH = 6
    # index_params = {'algorithm':FLANN_INDEX_KDTREE, 'trees':10}
    index_params = {'algorithm':FLANN_INDEX_LSH,
                    'table_number':8,
                    'key_size':12,
                    'multi_probe_level':2
    }

    search_params = {'checks':3} # 或者传递空字典
 
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(des1, des2, k=2)
 
    # 只需要绘制好的匹配，所以创建一个掩膜
    matchesMask = [[0, 0] for i in range(len(matches))]
    matchCounts = 0
    if len(matchesMask) !=0:
        # # 按照Lowe的论文进行比率测试 (SIFT)
        # for i, (m, n) in enumerate(matches):
        #     if m.distance < 0.5 * n.distance:
        #         matchesMask[i] = [1, 0]
        #         matchCounts += 1
        # 按照Lowe的论文进行比率测试 (ORB)
        for i,match in enumerate(matches):
            if len(match) == 2:
                m,n=match
                if m.distance < 0.6 * n.distance:
                    matchesMask[i] = [1, 0]
                    matchCounts += 1
        matchPercent = matchCounts/len(matchesMask)
    else:
        matchPercent=0
    if debug:
        endTime = datetime.datetime.now()-startTime
        print('Match Points:',matchCounts)
        print('Match Percents:{:.2%}'.format(matchPercent))
        print('Time Elapsed:',endTime)
        draw_params = {'matchColor':(0, 255, 0),
                       'singlePointColor':(255, 0, 0),
                       'matchesMask':matchesMask,
                       'flags':0}
        img3 = cv2.drawMatchesKnn(img1, kp1, img2, kp2, matches, None, **draw_params)
        return matchPercent,img3
    return matchPercent
