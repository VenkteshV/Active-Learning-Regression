from ssbase import SemiSupervisedBase


def main():
    names = ["forestfires", "concrete", "cps", "pm10", "housing", "redwine", "whitewine", "bike"]
    #names = ["concrete", "cps", "pm10", "housing"]
    #names = ["forestfires", "concrete", "housing"]
    #names = ["concrete"]
    methods = ["random", "bemcm", "qbc", "greedy", "qbc2"]
    methods = ["random", "bemcm", "qbc", "greedy"]
    methods = ["random", "greedy"]
    methods = ["random", "random2", "random3", "greedy", "greedy2", "greedy3", "qbc", "qbc2", "qbc3"]
    methods = ["random", "bemcm", "qbc", "greedy"]
    for name in names:
        for method in methods:
            s = SemiSupervisedBase(name, method)
            s.get_average()


if __name__ == "__main__":
    main()
