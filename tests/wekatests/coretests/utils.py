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

# utils.py
# Copyright (C) 2014-2015 Fracpete (pythonwekawrapper at gmail dot com)

import unittest
from weka.core.classes import join_options, split_options, from_commandline
import weka.core.jvm as jvm
import wekatests.tests.weka_test as weka_test


class TestUtils(weka_test.WekaTest):

    def test_split_options(self):
        """
        Tests the split_options method.
        """
        self.assertEqual(0, len(split_options("")))
        self.assertEqual(2, len(split_options("-t /some/where/test.arff")))

    def test_join_options(self):
        """
        Tests the join_options method.
        """
        self.assertEqual("", str(join_options([])))
        self.assertEqual("-t /some/where/test.arff", str(join_options(["-t", "/some/where/test.arff"])))

    def test_from_and_to_commandline(self):
        """
        Tests the from_commandline and to_commandline methods.
        """
        cmdline = "weka.classifiers.trees.J48 -C 0.3 -M 4"
        cls = from_commandline(
            cmdline=cmdline, classname="weka.classifiers.Classifier")
        self.assertIsNotNone(cls)
        self.assertEqual(cmdline, cls.to_commandline())


def suite():
    """
    Returns the test suite.
    :return: the test suite
    :rtype: unittest.TestSuite
    """
    return unittest.TestLoader().loadTestsFromTestCase(TestUtils)


if __name__ == '__main__':
    jvm.start()
    unittest.TextTestRunner().run(suite())
    jvm.stop()
