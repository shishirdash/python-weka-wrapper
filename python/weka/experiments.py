# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# experiments.py
# Copyright (C) 2014 Fracpete (fracpete at gmail dot com)

import logging
import javabridge
import weka.core.jvm as jvm
import weka.core.utils as utils
from weka.core.classes import OptionHandler, Range
from weka.core.dataset import Instances
from weka.classifiers import Classifier

# logging setup
logger = logging.getLogger("weka.experiments")


class Experiment(OptionHandler):
    """
    Wrapper class for an experiment.
    """

    def __init__(self, classname=None, jobject=None):
        """
        Initializes the specified experiment using either the classname or the supplied JB_Object.
        :param classname: the classname of the experiment
        :param jobject: the JB_Object to use
        """
        if jobject is None:
            jobject = Experiment.new_instance(classname)
        if classname is None:
            classname = utils.get_classname(jobject)
        self.classname = classname
        super(Experiment, self).__init__(jobject)


class SimpleExperiment(OptionHandler):
    """
    Ancestor for simple experiments.
    See following URL for how to use the Experiment API:
    http://weka.wikispaces.com/Using+the+Experiment+API
    """

    def __init__(self, jobject=None, classification=True, runs=10, datasets=[], classifiers=[], result=None):
        """
        Initializes the experiment.
        :param classification: whether to perform classification or regression
        :param runs: the number of runs to perform
        :param datasets: the filenames of datasets to use in the experiment
        :param classifiers: the Classifier objects or commandline strings to use in the experiment
        :param result: the filename of the file to store the results in
        """

        if not jobject is None:
            self.enforce_type(jobject, "weka.experiment.Experiment")

        self.classification = classification
        self.runs           = runs
        self.datasets       = datasets[:]
        self.classifiers    = classifiers[:]
        self.result         = result
        self.jobject        = jobject

    def configure_splitevaluator(self):
        """
        Configures and returns the SplitEvaluator and Classifier instance as tuple.
        :rtype: tuple
        """
        if self.classification:
            speval = javabridge.make_instance("weka/experiment/ClassifierSplitEvaluator", "()V")
        else:
            speval = javabridge.make_instance("weka/experiment/RegressionSplitEvaluator", "()V")
        classifier = javabridge.call(speval, "getClassifier", "()Lweka/classifiers/Classifier;")
        return speval, classifier

    def configure_resultproducer(self):
        """
        Configures and returns the ResultProducer and PropertyPath as tuple.
        :rtype: tuple
        """
        raise Exception("Not implemented!")

    def setup(self):
        """
        Initializes the experiment.
        """
        if not self.jobject is None:
            return

        self.jobject = javabridge.make_instance("weka/experiment/Experiment", "()V")

        # basic options
        javabridge.call(
            self.jobject, "setPropertyArray", "(Ljava/lang/Object;)V",
            jvm.ENV.make_object_array(0, jvm.ENV.find_class("weka/classifiers/Classifier")))
        javabridge.call(
            self.jobject, "setUsePropertyIterator", "(Z)V", True)
        javabridge.call(
            self.jobject, "setRunLower", "(I)V", 1)
        javabridge.call(
            self.jobject, "setRunUpper", "(I)V", self.runs)

        # setup result producer
        rproducer, prop_path = self.configure_resultproducer()
        javabridge.call(
            self.jobject, "setResultProducer", "(Lweka/experiment/ResultProducer;)V", rproducer)
        javabridge.call(
            self.jobject, "setPropertyPath", "([Lweka/experiment/PropertyNode;)V", prop_path)

        # classifiers
        classifiers = jvm.ENV.make_object_array(len(self.classifiers), jvm.ENV.find_class("weka/classifiers/Classifier"))
        for i, classifier in enumerate(self.classifiers):
            if type(classifier) is Classifier:
                jvm.ENV.set_object_array_element(classifiers, i, classifier.jobject)
            else:
                jvm.ENV.set_object_array_element(classifiers, i, utils.from_commandline(classifier).jobject)
        javabridge.call(
            self.jobject, "setPropertyArray", "(Ljava/lang/Object;)V",
            classifiers)

        # datasets
        datasets = javabridge.make_instance("javax/swing/DefaultListModel", "()V")
        for dataset in self.datasets:
            f = javabridge.make_instance("java/io/File", "(Ljava/lang/String;)V", dataset)
            javabridge.call(datasets, "addElement", "(Ljava/lang/Object;)V", f)
        javabridge.call(
            self.jobject, "setDatasets", "(Ljavax/swing/DefaultListModel;)V", datasets)

        # output file
        if str(self.result).lower().endswith(".arff"):
            rlistener = javabridge.make_instance("weka/experiment/InstancesResultListener", "()V")
        elif str(self.result).lower().endswith(".csv"):
            rlistener = javabridge.make_instance("weka/experiment/CSVResultListener", "()V")
        else:
            raise Exception("Unhandled output format for results: " + self.result)
        rfile = javabridge.make_instance("java/io/File", "(Ljava/lang/String;)V", self.result)
        javabridge.call(
            rlistener, "setOutputFile", "(Ljava/io/File;)V", rfile)
        javabridge.call(
            self.jobject, "setResultListener", "(Lweka/experiment/ResultListener;)V", rlistener)

    def run(self):
        """
        Executes the experiment.
        """
        logger.info("Initializing...")
        javabridge.call(self.jobject, "initialize", "()V")
        logger.info("Running...")
        javabridge.call(self.jobject, "runExperiment", "()V")
        logger.info("Finished...")
        javabridge.call(self.jobject, "postProcess", "()V")

    def get_experiment(self):
        """
        Returns the internal experiment, if set up, otherwise None.
        :rtype: Experiment
        """
        if self.jobject is None:
            return None
        else:
            return Experiment(self.jobject)

    @classmethod
    def load(cls, filename):
        """
        Loads the experiment from disk.
        :param filename: the filename of the experiment to load
        :rtype: Experiment
        """
        jobject = javabridge.static_call(
            "weka/experiment/Experiment", "read", "(Ljava/lang/String;)Lweka/experiment/Experiment;",
            filename)
        return Experiment(jobject=jobject)

    @classmethod
    def save(cls, filename, experiment):
        """
        Saves the experiment to disk.
        :param filename: the filename to save the experiment to
        :param experiment: the Experiment to save
        """
        javabridge.static_call(
            "weka/experiment/Experiment", "write", "(Ljava/lang/String;Lweka/experiment/Experiment;)V",
            filename, experiment.jobject)


class SimpleCrossValidationExperiment(SimpleExperiment):
    """
    Performs a simple cross-validation experiment. Can output the results either in ARFF or CSV.
    """

    def __init__(self, classification=True, runs=10, folds=10, datasets=[], classifiers=[], result=None):
        """
        Initializes the experiment.
        :param runs: the number of runs to perform
        :param folds: the number folds to use for CV
        :param datasets: the filenames of datasets to use in the experiment
        :param classifiers: the Classifier objects to use in the experiment
        :param result: the filename of the file to store the results in
        """

        if runs < 1:
            raise Exception("Number of runs must be at least 1!")
        if folds < 2:
            raise Exception("Number of folds must be at least 2!")
        if len(datasets) == 0:
            raise Exception("No datasets provided!")
        if len(classifiers) == 0:
            raise Exception("No classifiers provided!")
        if result is None:
            raise Exception("No filename for results provided!")

        super(SimpleCrossValidationExperiment, self).__init__(
            classification=classification, runs=runs, datasets=datasets,
            classifiers=classifiers, result=result)

        self.folds = folds

    def configure_resultproducer(self):
        """
        Configures and returns the ResultProducer and PropertyPath as tuple.
        :rtype: tuple
        """
        rproducer = javabridge.make_instance("weka/experiment/CrossValidationResultProducer", "()V")
        javabridge.call(rproducer, "setNumFolds", "(I)V", self.folds)
        speval, classifier = self.configure_splitevaluator()
        javabridge.call(rproducer, "setSplitEvaluator", "(Lweka/experiment/SplitEvaluator;)V", speval)
        prop_path = jvm.ENV.make_object_array(2, jvm.ENV.find_class("weka/experiment/PropertyNode"))
        cls  = jvm.ENV.find_class("weka/experiment/CrossValidationResultProducer")
        desc = javabridge.make_instance(
            "java/beans/PropertyDescriptor", "(Ljava/lang/String;Ljava/lang/Class;)V", "splitEvaluator", cls)
        node = javabridge.make_instance(
            "weka/experiment/PropertyNode", "(Ljava/lang/Object;Ljava/beans/PropertyDescriptor;Ljava/lang/Class;)V",
            speval, desc, cls)
        jvm.ENV.set_object_array_element(prop_path, 0, node)
        cls  = jvm.ENV.get_object_class(speval)
        desc = javabridge.make_instance(
            "java/beans/PropertyDescriptor", "(Ljava/lang/String;Ljava/lang/Class;)V", "classifier", cls)
        node = javabridge.make_instance(
            "weka/experiment/PropertyNode", "(Ljava/lang/Object;Ljava/beans/PropertyDescriptor;Ljava/lang/Class;)V",
            jvm.ENV.get_object_class(speval), desc, cls)
        jvm.ENV.set_object_array_element(prop_path, 1, node)

        return rproducer, prop_path


class SimpleRandomSplitExperiment(SimpleExperiment):
    """
    Performs a simple random split experiment. Can output the results either in ARFF or CSV.
    """

    def __init__(self, classification=True, runs=10, percentage=66.6, preserve_order=False, datasets=[], classifiers=[], result=None):
        """
        Initializes the experiment.
        :param runs: the number of runs to perform
        :param percentage: the percentage to use for training
        :param preserve_order: whether to preserve the order in the datasets
        :param datasets: the filenames of datasets to use in the experiment
        :param classifiers: the Classifier objects to use in the experiment
        :param result: the filename of the file to store the results in
        """

        if runs < 1:
            raise Exception("Number of runs must be at least 1!")
        if percentage <= 0:
            raise Exception("Percentage for training must be >0!")
        if percentage >= 100:
            raise Exception("Percentage for training must be <100!")
        if len(datasets) == 0:
            raise Exception("No datasets provided!")
        if len(classifiers) == 0:
            raise Exception("No classifiers provided!")
        if result is None:
            raise Exception("No filename for results provided!")

        super(SimpleRandomSplitExperiment, self).__init__(
            classification=classification, runs=runs, datasets=datasets,
            classifiers=classifiers, result=result)

        self.percentage     = percentage
        self.preserve_order = preserve_order

    def configure_resultproducer(self):
        """
        Configures and returns the ResultProducer and PropertyPath as tuple.
        :rtype: tuple
        """
        rproducer = javabridge.make_instance("weka/experiment/RandomSplitResultProducer", "()V")
        javabridge.call(rproducer, "setRandomizeData", "(Z)V", not self.preserve_order)
        javabridge.call(rproducer, "setTrainPercent", "(D)V", self.percentage)
        speval, classifier = self.configure_splitevaluator()
        javabridge.call(rproducer, "setSplitEvaluator", "(Lweka/experiment/SplitEvaluator;)V", speval)
        prop_path = jvm.ENV.make_object_array(2, jvm.ENV.find_class("weka/experiment/PropertyNode"))
        cls  = jvm.ENV.find_class("weka/experiment/RandomSplitResultProducer")
        desc = javabridge.make_instance(
            "java/beans/PropertyDescriptor", "(Ljava/lang/String;Ljava/lang/Class;)V", "splitEvaluator", cls)
        node = javabridge.make_instance(
            "weka/experiment/PropertyNode", "(Ljava/lang/Object;Ljava/beans/PropertyDescriptor;Ljava/lang/Class;)V",
            speval, desc, cls)
        jvm.ENV.set_object_array_element(prop_path, 0, node)
        cls  = jvm.ENV.get_object_class(speval)
        desc = javabridge.make_instance(
            "java/beans/PropertyDescriptor", "(Ljava/lang/String;Ljava/lang/Class;)V", "classifier", cls)
        node = javabridge.make_instance(
            "weka/experiment/PropertyNode", "(Ljava/lang/Object;Ljava/beans/PropertyDescriptor;Ljava/lang/Class;)V",
            jvm.ENV.get_object_class(speval), desc, cls)
        jvm.ENV.set_object_array_element(prop_path, 1, node)

        return rproducer, prop_path


class ResultMatrix(OptionHandler):
    """
    For generating results from an Experiment run.
    """

    def __init__(self, classname=None, jobject=None):
        """
        Initializes the specified ResultMatrix using either the classname or the supplied JB_Object.
        :param classname: the classname of the ResultMatrix
        :param jobject: the JB_Object to use
        """
        if jobject is None:
            jobject = ResultMatrix.new_instance(classname)
        if classname is None:
            classname = utils.get_classname(jobject)
        self.classname = classname
        self.enforce_type(jobject, "weka.experiment.ResultMatrix")
        super(ResultMatrix, self).__init__(jobject)

    def to_string_matrix(self):
        """
        Returns the matrix as a string.
        :rtype: str
        """
        return javabridge.call(self.jobject, "toStringMatrix", "()V")

    def to_string_key(self):
        """
        Returns a key for all the col names, for better readability if the names got cut off.
        :rtype: str
        """
        return javabridge.call(self.jobject, "toStringKey", "()V")

    def to_string_header(self):
        """
        Returns the header of the matrix as a string.
        :rtype: str
        """
        return javabridge.call(self.jobject, "toStringHeader", "()V")

    def to_string_summary(self):
        """
        returns the summary as string.
        :rtype: str
        """
        return javabridge.call(self.jobject, "toStringSummary", "()V")

    def to_string_ranking(self):
        """
        Returns the ranking in a string representation.
        :rtype: str
        """
        return javabridge.call(self.jobject, "toStringRanking", "()V")


class Tester(OptionHandler):
    """
    For generating statistical results from an experiment.
    """

    def __init__(self, classname=None, jobject=None):
        """
        Initializes the specified tester using either the classname or the supplied JB_Object.
        :param classname: the classname of the tester
        :param jobject: the JB_Object to use
        """
        if jobject is None:
            jobject = Tester.new_instance(classname)
        if classname is None:
            classname = utils.get_classname(jobject)
        self.classname = classname
        self.enforce_type(jobject, "weka.experiment.Tester")
        self.columns_determined = False
        self.dataset_columns = None
        self.run_column = None
        self.fold_column = None
        self.result_columns = None
        super(Tester, self).__init__(jobject)

    def set_resultmatrix(self, matrix):
        """
        Sets the ResultMatrix to use.
        :param matrix: the ResultMatrix instance to use
        """
        javabridge.call(self.jobject, "setResultMatrix", "(Lweka/experiment/ResultMatrix;)V", matrix.jobject)

    def get_resultmatrix(self):
        """
        Returns the ResultMatrix instance in use.
        :rtype: ResultMatrix
        """
        return ResultMatrix(javabridge.call(self.jobject, "getResultMatrix", "()Lweka/experiment/ResultMatrix;"))

    def set_instances(self, data):
        """
        Sets the data to use for analysis.
        :param inst: the Instances to analyze
        """
        javabridge.call(self.jobject, "setInstances", "(Lweka/core/Instances;)V", data.jobject)
        self.columns_determined = False

    def get_instances(self):
        """
        Retruns the data used in the analysis.
        :rtype: Instances
        """
        inst = javabridge.call(self.jobject, "getInstances", "()Lweka/core/Instances;")
        if inst is None:
            return None
        else:
            return Instances(inst)

    def set_dataset_columns(self, col_names):
        """
        Sets the list of column names that identify uniquely a dataset.
        :param col_names: the list of attribute names
        """
        self.dataset_columns = col_names[:]

    def set_run_column(self, col_name):
        """
        Sets the column name that holds the Run number.
        :param col_name: the attribute name
        """
        self.run_column = col_name

    def set_fold_column(self, col_name):
        """
        Sets the column name that holds the Fold number.
        :param col_name: the attribute name
        """
        self.fold_column = col_name

    def set_result_columns(self, col_names):
        """
        Sets the list of column names that identify uniquely a result (eg classifier + options + ID).
        :param col_names: the list of attribute names
        """
        self.result_columns = col_names[:]

    def init_columns(self):
        """
        Sets the column indices based on the supplied names if necessary.
        """
        if self.columns_determined:
            return
        data = self.get_instances()
        if data is None:
            print("No instances set, cannot determine columns!")
            return

        # dataset
        if self.dataset_columns is None:
            raise Exception("No dataset columns set!")
        cols = ""
        for name in self.dataset_columns:
            att = data.get_attribute_by_name(name)
            if att is None:
                raise Exception("Dataset column not found: " + name)
            if len(cols) > 0:
                cols += ","
            cols += str(att.get_index() + 1)
        javabridge.call(
            self.jobject, "setDatasetKeyColumns", "(Lweka/core/Range;)V", Range(ranges=cols).jobject)

        # run
        if self.run_column is None:
            raise Exception("No run columnn set!")
        att = data.get_attribute_by_name(self.run_column)
        if att is None:
            raise Exception("Run column not found: " + self.run_column)
        javabridge.call(
            self.jobject, "setRunColumn", "(I)V", att.get_index())

        # fold
        if not self.fold_column is None:
            att = data.get_attribute_by_name(self.fold_column)
            if att is None:
                raise Exception("Fold column not found: " + self.fold_column)
            javabridge.call(
                self.jobject, "setFoldColumn", "(I)V", att.get_index())

        # result
        if self.result_columns is None:
            raise Exception("No reset columns set!")
        cols = ""
        for name in self.result_columns:
            att = data.get_attribute_by_name(name)
            if att is None:
                raise Exception("Result column not found: " + name)
            if len(cols) > 0:
                cols += ","
            cols += str(att.get_index() + 1)
        javabridge.call(
            self.jobject, "setResultsetKeyColumns", "(Lweka/core/Range;)V", Range(ranges=cols).jobject)

        self.columns_determined = True

    def header(self, comparison_column):
        """
        Creates a "header" string describing the current resultsets.
        :param comparison_column: the index of the column to compare against
        :rtype: str
        """
        self.init_columns()
        return javabridge.call(
            self.jobject, "header", "(I)Ljava/lang/String;", comparison_column)

    def multi_resultset_full(self, base_resultset, comparison_column):
        """
        Creates a comparison table where a base resultset is compared to the other resultsets.
        :param base_resultset: the index of the base resultset
        :param comparison_column: the index of the column to compare against
        :rtype: str
        """
        return javabridge.call(
            self.jobject, "multiResultsetFull", "(II)Ljava/lang/String;", base_resultset, comparison_column)

    def multi_resultset_ranking(self, comparison_column):
        """
        Creates a ranking.
        :param comparison_column: the index of the column to compare against
        :rtype: str
        """
        return javabridge.call(
            self.jobject, "multiResultsetRanking", "(I)Ljava/lang/String;", comparison_column)

    def multi_resultset_summary(self, comparison_column):
        """
        Carries out a comparison between all resultsets, counting the number of datsets where one resultset
        outperforms the other.
        :param comparison_column: the index of the column to compare against
        :rtype: str
        """
        return javabridge.call(
            self.jobject, "multiResultsetSummary", "(I)Ljava/lang/String;", comparison_column)