import unittest
import pandas as pd
from dfs_stack import qb_wr_stack

TEST_DF = pd.read_csv('test_utils/DKSalaries-test.csv')
'''TEST_DF has various corruptions of data to be used for tests

ARI: No QB
ATL: No WRs/TEs
JAX: Only has a DST

'''

class TestFunctions(unittest.TestCase):
    def test_qb_wr_stack_no_player_error(self):
        with self.assertRaises(Exception):
            qb_wr_stack(TEST_DF, "JAX")

    def test_qb_wr_stack_no_qb_error(self):
        with self.assertRaises(Exception):
            qb_wr_stack(TEST_DF, "ARI")

    def test_qb_wr_stack_no_flex_error(self):
        with self.assertRaises(Exception):
            qb_wr_stack(TEST_DF, "ATL")
    
if __name__ == '__main__':
    unittest.main()