import matplotlib.pyplot as plt
import numpy as np
from sklearn import datasets, linear_model
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.utils import resample
import pickle
import json
import math
import random
from timer import Timer


class SemiSupervisedBase:

    def __init__(self, name, method = "random"):
        # Configuration variables.
        self.num_runs = 30
        self.num_iterations = 11
        self.label_percent = 0.1
        self.test_percent = 0.2
        self.batch_percent = 0.03
        # Initialize variables.
        self.cache = None
        self.name = name
        self.method = method
        # Read data.
        with open("data/{}.dat".format(name), "rb") as infile:
            self.data = pickle.loads(infile.read())

    def get_average(self):
        print("Start process for {} {}...".format(self.name, self.method))
        mae = []
        for i in range(self.num_runs):
            mae.append(self.process())
        mae = np.array(mae)

        # Calculate Average
        N = mae.shape[0]
        M = mae.shape[1]
        x = list(range(M))
        y_average = np.zeros(M)
        for i in range(N):
            y_average += mae[i]
        y_average /= N

        # Calculate Standard Deviation
        y_stddev = np.zeros(M)
        for i in range(N):
            y_stddev += (mae[i] - y_average) * (mae[i] - y_average)
        y_stddev = np.sqrt(y_stddev / N)

        # Write output.
        with open("results/{}.txt".format(self.name + "_" + self.method), "w") as outfile:
            outfile.write("x\ty_average\ty_stddev\n")
            for i in range(len(x)):
                outfile.write(str(x[i]) + "\t" + str(y_average[i]) + "\t" + str(y_stddev[i]) + "\n")
        
        # Build 1 stddev.
        y_top = y_average + y_stddev
        y_bottom = y_average - y_stddev

        # Plot range
        fig, ax = plt.subplots()
        ax.plot(x, y_average, color="black")
        ax.plot(x, y_top, x, y_bottom, color="black")
        ax.fill_between(x, y_average, y_top, where=y_top>y_average, facecolor="green", alpha=0.5)
        ax.fill_between(x, y_average, y_bottom, where=y_bottom<=y_average, facecolor="red", alpha=0.5)
        #plt.show()

    def process(self):
        """
        This runs the the 
        
        Args:
            None
        Return:
            None
        """
        Timer.start("Train")
        # Get counts for different sets.
        count = self.data["data"].shape[0]
        labeled_count = int(count * self.label_percent)
        test_count = int(count * self.test_percent)
        unlabeled_count = count - labeled_count - test_count
        self.batch_count = int(count * self.batch_percent)
        pos_list = list(range(count))
        # Split the data into training/testing sets
        random.shuffle(pos_list)
        self.labeled_pos_list = pos_list[:labeled_count]
        self.unlabeled_pos_list = pos_list[labeled_count:(labeled_count+unlabeled_count)]
        self.test_pos_list = pos_list[(labeled_count+unlabeled_count):]

        mae_list = []
        for j in range(self.num_iterations):
            Timer.start("{} iteration".format(j))
            mae = self.train()
            mae_list.append(mae)
            self.update_labeled()
            total_time = Timer.stop("{} iteration".format(j))
            #print("Iteration #{} {:.2f}s".format((j+1), total_time))
        total_time = Timer.stop("Train")
        print("Full Training Cycle {:.2f}s".format(total_time))
        return np.array(mae_list)

    def train(self):
        data_X_train = self.data["data"][ self.labeled_pos_list ]
        data_X_test = self.data["data"][ self.test_pos_list ]

        # Split the targets into training/testing sets
        data_y_train = self.data["target"][ self.labeled_pos_list ]
        data_y_test = self.data["target"][ self.test_pos_list ]

        # Create linear regression object
        regr = linear_model.LinearRegression()
        # Use linear regression using SGD
        #regr = linear_model.SGDRegressor(alpha=0.05, learning_rate='constant', penalty='none')

        # Train the model using the training sets
        regr.fit(data_X_train, data_y_train)

        # Make predictions using the testing set
        data_y_pred = regr.predict(data_X_test)

        # Get prediction error using mean absolute error.
        mae = get_mean_absolute_error(data_y_test, data_y_pred)
        return mae

    def update_labeled(self):
        if self.method == "random":
            self.update_labeled_random()
        elif self.method == "greedy":
            self.update_labeled_greedy()
        elif self.method == "qbc":
            self.update_labeled_qbc()
        else:
            print("Method '{}' is unknown.".format(self.method))
            exit()

    def update_labeled_random(self):
        Timer.start("Random")
        self.labeled_pos_list.extend(self.unlabeled_pos_list[:self.batch_count])
        self.unlabeled_pos_list = self.unlabeled_pos_list[(self.batch_count+1):]
        total_time = Timer.stop("Random")
        #print("Random Update {:.2f}s".format(total_time))

    def update_labeled_greedy(self):
        Timer.start("Greedy")
        for i in range(self.batch_count):
            max_dist = 0
            max_pos = -1
            for j in range(len(self.unlabeled_pos_list)):
                dist = self.get_min_distance(j)
                if dist > max_dist:
                    max_dist = dist
                    max_pos = self.unlabeled_pos_list[j]
            self.labeled_pos_list.append(max_pos)
            self.unlabeled_pos_list.remove(max_pos)
        total_time = Timer.stop("Greedy")
        #print("Greedy Update {:.2f}s".format(total_time))

    def update_labeled_qbc(self):
        Timer.start("QBC")
        # Build the committee.
        models = []
        for i in range(4):
            # Build bootstrap of training data.
            bootstrap_labeled_pos_list = resample(self.labeled_pos_list)

            data_X_train = self.data["data"][ bootstrap_labeled_pos_list ]

            # Split the targets into training/testing sets
            data_y_train = self.data["target"][ bootstrap_labeled_pos_list ]

            # Create linear regression object
            regr = linear_model.LinearRegression()

            # Train the model using the training sets
            regr.fit(data_X_train, data_y_train)
            models.append(regr)
        
        variances = []
        for i in range(len(self.unlabeled_pos_list)):
            pos = self.unlabeled_pos_list[i]
            ys = []
            yave = 0
            for j in range(len(models)):
                y = models[j].predict(self.data["data"][pos:(pos+1), :])[0]
                ys.append(y)
                yave += y
            yave /= (len(models) * 1.0)
            variance = 0
            for j in range(len(models)):
                variance += (ys[j] - yave) * (ys[j] - yave)
            variances.append((variance, pos))
        variances.sort(reverse = True)
        for i in range(self.batch_count):
            self.labeled_pos_list.append(variances[i][1])
            self.unlabeled_pos_list.remove(variances[i][1])
        total_time = Timer.stop("QBC")
        #print("Greedy Update {:.2f}s".format(total_time))

    def get_min_distance(self, i):
        min_dist = None
        min_pos = -1
        for j in self.labeled_pos_list:
            dist = self.calc_distance(i, j)
            if min_dist is None or dist < min_dist:
                min_dist = dist
                min_pos = j
        return min_dist

    def calc_distance(self, i, j):
        if self.cache is None:
            self.cache = np.ones((self.data["data"].shape[0], self.data["data"].shape[0])) * -1
        if self.cache[i, j] == -1:
            x = self.data["data"][i]
            y = self.data["data"][j]
            self.cache[i, j] = np.linalg.norm(x-y)
        return self.cache[i, j]


def get_mean_absolute_error(y_actual, y_predict):
    T = y_actual.size
    mae = 0
    for i in range(T):
        mae += abs(y_actual[i] - y_predict[i])
    mae = mae / T
    return mae