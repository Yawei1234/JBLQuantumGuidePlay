def distSignal(dist):
    if (dist > 100):
        # gray
        color = (128, 128, 128)
        silence = 1

    elif (dist > 60):
        # purple
        silence = 0.7
        color = (255, 0, 255)
    elif (dist > 50):
        # cyan
        silence = 0.350
        color = (255, 255, 0)
    elif (dist > 40):
        # yellow
        silence = 0.150
        color = (0, 255, 255)
    elif (dist > 20):
        # orange
        silence = 0.05
        color = (0, 128, 255)
    else:
        # red
        color = (0, 0, 255)
        silence = 0
    return silence, color
