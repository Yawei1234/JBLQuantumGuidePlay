import math


def distSignal(dist, maxDistance=None):

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

    if maxDistance is not None:
        silence = 0.1 + dist / maxDistance

    return silence, color


class EuclideanDistTracker:
    def __init__(self):
        # Store the center positions of the objects
        self.center_points = {}
        # Keep the count of the IDs
        # each time a new object id detected, the count will increase by one
        self.id_count = 0

    def update(self, objects_rect):
        # Objects boxes and ids
        objects_bbs_ids = []

        # Get center point of new object
        for rect in objects_rect:
            x, y, w, h, id, angle, px, py = rect
            recId = id
            # find the center of the rect
            cx = (x + x + w) // 2
            cy = (y + y + h) // 2

            # print("\n\ncenter_points_", len(
            #     self.center_points), "\n", self.center_points)
            # print("current_rect", rect)
            # print("current_center", (cx, cy))

            # Find out if that object was detected already
            same_object_detected = False
            for id, pt in self.center_points.items():
                dist = int(math.hypot(cx - pt[0], cy - pt[1]))

                # print("\n **** pt", pt)
                # print("dist:", dist, "\n" "id", id, "center:", (pt[0], pt[1]),
                #       "rect:", rect, "center_check", (cx, cy), "****\n")

                if dist < 30:
                    # print("already detected", (cx, cy))
                    self.center_points[id] = (cx, cy, recId)
                    objects_bbs_ids.append(
                        [x, y, w, h, id, recId, angle, px, py])
                    same_object_detected = True
                    break

            # New object is detected we assign the ID to that object
            if same_object_detected is False:
                # print("new object detected", (cx, cy, recId))
                self.center_points[self.id_count] = (cx, cy, recId)
                objects_bbs_ids.append(
                    [x, y, w, h, self.id_count, recId, angle, px, py])
                self.id_count += 1
            # else:
            #     print("same object detected")

        # Clean the dictionary by center points to remove IDS not used anymore
        new_center_points = {}
        for obj_bb_id in objects_bbs_ids:
            # _, _, _, _, object_id, realId, angle = obj_bb_id

            object_id = obj_bb_id[4]
            realId = obj_bb_id[5]
            angle = obj_bb_id[6]

            center = self.center_points[object_id]
            center = (center[0], center[1], realId)
            # print("center_packed", center)
            new_center_points[object_id] = center

        # Update dictionary with IDs not used removed
        self.center_points = new_center_points.copy()
        return objects_bbs_ids
