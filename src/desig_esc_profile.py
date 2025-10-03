from os import path
import csv
import math
import numpy as np

def interesting_function(t_s):
    retime_s = t_s * 2 * math.pi
    return ((
        math.sin(retime_s)
        + 3 * math.cos(3 * retime_s)
        + 5 * math.sin(2 * retime_s)
    ) / 9 + 1) / 2

def gradual(t_s):
    s = 8/60 # denominator is test period(i.e. 60s)
    rt_s = t_s * s

    out = (
        math.tanh(rt_s-2) - math.tanh(rt_s - 6)
    ) / 2
    return out

def step(t_s):
    def u(t):
        return 0 if t < 0 else 1
    out = 0
    for i in range(25):
        out += u(t_s-i*4)*(t_s-i*4)*(-1)**i
    return out*2

def step_reverse(t_s):
    if t_s < 3:
        return t_s * 100/3
    elif t_s < 8:
        return 90
    elif t_s < 13:
        return 80
    elif t_s < 18:
        return 70
    elif t_s < 23:
        return 60
    elif t_s < 28:
        return 50
    elif t_s < 33:
        return 40
    elif t_s < 38:
        return 30
    elif t_s < 43:
        return 20
    elif t_s < 48:
        return 10
    elif t_s < 53:
        return 0
    return 0

# with open(path.join(__file__, "../profiles/interesting.csv"), "w", newline="") as file:
#     writer = csv.writer(file)
#     for i in range(0, int(10e3), 100):
#         writer.writerow(
#             [i, interesting_function(i / 1000) * 100]
#         )
# with open(path.join(__file__, "../profiles/gradual_ramp.csv"), "w", newline="") as file:
#     writer = csv.writer(file)
#     for i in range(0, int(60e3), 100):
#         writer.writerow(
#             [i, gradual(i / 1000) * 100]
#         )
# with open(path.join(__file__, "../profiles/step_ramp.csv"), "w", newline="") as file:
#     writer = csv.writer(file)
#     for i in np.arange(stop=50, step=0.1):
#         writer.writerow(
#             (i*1000, step(2*i))
#         )
#     writer.writerow((1000, 0))
with open(path.join(__file__, "../profiles/step_ramp_invert.csv"), "w", newline="") as file:
    writer = csv.writer(file)
    for i in np.arange(start = 0, stop = 60, step=0.25):
        writer.writerow(
            (i*1000, step_reverse(i))
        )
    writer.writerow((1000, 0))

# import matplotlib.pyplot as plt
# plt.plot([i for i in range(50)], [step(2*i) for i in range(50)])
# plt.show()