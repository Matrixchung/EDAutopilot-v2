from utils import *
pyautogui.PAUSE = 1
pyautogui.FAILSAFE = True
def addOneInOneSec(sharedMem):
    # print(sharedMem)
    shmExists = shared_memory.SharedMemory(name=sharedMem)
    array = np.ndarray(shape=1,dtype=np.int,buffer=shmExists.buf)
    while 1:
        array[0] += 1
        # print ('add 1')
        time.sleep(0.1)
    shmExists.close()
def createSharedBlock():
    a = np.ndarray(shape=1,dtype=np.int)
    a[0] = 0
    shr = shared_memory.SharedMemory(create=True,size=a.nbytes)
    npArray = np.ndarray(a.shape,dtype=np.int,buffer=shr.buf)
    npArray[:] = a[:]
    return shr,npArray
if __name__ == '__main__':
    print("Creating shared memory block...")
    shr, npArray = createSharedBlock()
    print(shr.name)
    process = Process(target=addOneInOneSec,args=(shr.name,))
    process.daemon = True
    process.start()
    # process.join()
    print (npArray[0])
    timeCounts = 3
    while timeCounts>0:
        print('Sleep 1 sec')
        timeCounts -= 1
        time.sleep(1)
    print (npArray[0])
    timeCounts = 5
    while timeCounts>0:
        print('Sleep 1 sec')
        timeCounts -= 1
        time.sleep(1)
    print (npArray[0])
    process.terminate()
    shr.close()
    shr.unlink()

# # one dimension of the 2d array which is shared
# dim = 50

# import numpy as np
# from multiprocessing import shared_memory, Process, Lock
# from multiprocessing import cpu_count, current_process
# import time

# lock = Lock()

# def add_one(shr_name):

#     existing_shm = shared_memory.SharedMemory(name=shr_name)
#     np_array = np.ndarray((dim, dim,), dtype=np.int64, buffer=existing_shm.buf)
#     lock.acquire()
#     np_array[:] = np_array[0] + 1
#     lock.release()
#     time.sleep(10) # pause, to see the memory usage in top
#     print('added one')
#     existing_shm.close()

# def create_shared_block():

#     a = np.ones(shape=(dim, dim), dtype=np.int64)  # Start with an existing NumPy array

#     shm = shared_memory.SharedMemory(create=True, size=a.nbytes)
#     # # Now create a NumPy array backed by shared memory
#     np_array = np.ndarray(a.shape, dtype=np.int64, buffer=shm.buf)
#     np_array[:] = a[:]  # Copy the original data into shared memory
#     return shm, np_array

# if current_process().name == "MainProcess":
#     print("creating shared block")
#     shr, np_array = create_shared_block()

#     processes = []
#     for i in range(2):
#         _process = Process(target=add_one, args=(shr.name,))
#         processes.append(_process)
#         _process.start()

#     for _process in processes:
#         _process.join()

#     print("Final array")
#     print(np_array[:10])
#     print(np_array[10:])

#     shr.close()
#     shr.unlink()


