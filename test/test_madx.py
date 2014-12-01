# standard library
import unittest
import os

# utilities
import _compat

# tested class
from cpymad.madx import Madx


class TestMadx(unittest.TestCase, _compat.TestCase):

    """
    Test methods for the Madx class.

    The tests are directly based on the specifics of the sequence in

        test/data/lebt/init.madx

    Please compare this file for reference.
    """

    def setUp(self):
        self.mad = Madx()
        here = os.path.dirname(__file__)
        there = os.path.join(here, 'data', 'lebt', 'init.madx')
        self.doc = open(there).read()
        for line in self.doc.splitlines():
            self.mad._libmadx.input(line)

    def tearDown(self):
        del self.mad

    def test_command_log(self):
        """Check that the command log contains all input commands."""
        # create a new Madx instance that uses the history feature:
        history_filename = '_test_madx.madx.tmp'
        mad = Madx(command_log=history_filename)
        # feed some input and compare with history file:
        for line in self.doc.splitlines():
            mad.input(line)
        with open(history_filename) as history_file:
            history = history_file.read()
        self.assertEqual(history.strip(), self.doc.strip())
        # remove history file
        del mad
        os.remove(history_filename)

    # TODO:
    # def test_command(self):
    # def test_help(self):
    # def test_call(self):

    def _check_twiss(self, seq_name):
        beam = 'beam, ex=1, ey=2, particle=electron, sequence={0};'.format(seq_name)
        self.mad.command(beam)
        initial = dict(alfx=0.5, alfy=1.5,
                       betx=2.5, bety=3.5)
        # by explicitly specifying the 'columns' parameter a persistent copy
        # is returned. We check that this copy contains the data we want and
        # that it has a 'summary' attribute:
        twiss = self.mad.twiss(sequence=seq_name,
                               columns=['betx', 'bety', 'alfx', 'alfy'],
                               **initial)
        betx, bety = twiss['betx'], twiss['bety']
        alfx, alfy = twiss['alfx'], twiss['alfy']
        # Check initial values:
        self.assertAlmostEqual(twiss['alfx'][0], initial['alfx'])
        self.assertAlmostEqual(twiss['alfy'][0], initial['alfy'])
        self.assertAlmostEqual(twiss['betx'][0], initial['betx'])
        self.assertAlmostEqual(twiss['bety'][0], initial['bety'])
        self.assertAlmostEqual(twiss.summary['ex'], 1)
        self.assertAlmostEqual(twiss.summary['ey'], 2)
        # Check that keys are all lowercase:
        for k in twiss:
            self.assertEqual(k, k.lower())
        for k in twiss.summary:
            self.assertEqual(k, k.lower())

    def test_twiss_1(self):
        self._check_twiss('s1')     # s1 can be computed at start
        self._check_twiss('s1')     # s1 can be computed multiple times
        self._check_twiss('s2')     # s2 can be computed after s1

    def test_twiss_2(self):
        self._check_twiss('s2')     # s2 can be computed at start
        self._check_twiss('s1')     # s1 can be computed after s2

    def test_twiss_with_range(self):
        beam = 'beam, ex=1, ey=2, particle=electron, sequence=s1;'
        self.mad.command(beam)
        params = dict(alfx=0.5, alfy=1.5,
                      betx=2.5, bety=3.5,
                      columns=['betx', 'bety'],
                      sequence='s1')
        # Compute TWISS on full sequence, then on a sub-range, then again on
        # the full sequence. This checks that none of the range selections
        # have side-effects on each other:
        betx_full1 = self.mad.twiss(**params)['betx']
        betx_range = self.mad.twiss(range=('dr[2]', 'sb'), **params)['betx']
        betx_full2 = self.mad.twiss(**params)['betx']
        # Check that the results have the expected lengths:
        self.assertEqual(len(betx_full1), 9)
        self.assertEqual(len(betx_range), 4)
        self.assertEqual(len(betx_full2), 9)
        # Check numeric results. Since the first 3 elements of range and full
        # sequence are identical, equal results are expected. And non-equal
        # results afterwards.
        self.assertAlmostEqual(betx_range[0], betx_full1[1]) # dr:2, dr:1
        self.assertAlmostEqual(betx_range[1], betx_full1[2]) # qp:2, qp:1
        self.assertAlmostEqual(betx_range[2], betx_full1[3]) # dr:3, dr:2
        self.assertNotAlmostEqual(betx_range[3], betx_full1[4]) # sb, qp:2

    # def test_survey(self):
    # def test_aperture(self):
    # def test_use(self):
    # def test_match(self):
    # def test_verbose(self):

    def test_active_sequence(self):
        self.mad.command('beam, ex=1, ey=2, particle=electron, sequence=s1;')
        self.mad.active_sequence = 's1'
        self.assertEqual(self.mad.active_sequence, 's1')

    def test_get_sequence(self):
        self.assertRaises(ValueError, self.mad.get_sequence, 'sN')
        s1 = self.mad.get_sequence('s1')
        self.assertEqual(s1.name, 's1')

    def test_get_sequences(self):
        seqs = self.mad.get_sequences()
        self.assertItemsEqual([seq.name for seq in seqs],
                              ['s1', 's2'])

    def test_get_sequence_names(self):
        self.assertItemsEqual(self.mad.get_sequence_names(),
                              ['s1', 's2'])

    def test_evaluate(self):
        val = self.mad.evaluate("1/QP_K1")
        self.assertAlmostEqual(val, 0.5)

    # def test_sequence_beam(self):
    # def test_sequence_twiss(self):
    # def test_sequence_twissname(self):

    def _get_elems(self, seq_name):
        elems = self.mad.get_sequence(seq_name).get_elements()
        elem_dict = dict((el['name'], el) for el in elems)
        elem_idx = dict((el['name'], i) for i, el in enumerate(elems))
        return elem_dict, elem_idx

    def test_sequence_get_elements_s1(self):
        s1, idx = self._get_elems('s1')
        qp1 = s1['qp:1']
        qp2 = s1['qp:2']
        sb1 = s1['sb:1']
        self.assertLess(idx['qp:1'], idx['qp:2'])
        self.assertLess(idx['qp:2'], idx['sb:1'])
        self.assertAlmostEqual(qp1['at'], 1)
        self.assertAlmostEqual(qp2['at'], 3)
        self.assertAlmostEqual(sb1['at'], 5)
        self.assertAlmostEqual(qp1['l'], 1)
        self.assertAlmostEqual(qp2['l'], 1)
        self.assertAlmostEqual(sb1['l'], 2)
        self.assertAlmostEqual(float(qp1['k1']), 2)
        self.assertAlmostEqual(float(qp2['k1']), 2)
        self.assertAlmostEqual(float(sb1['angle']), 3.14/4)
        self.assertEqual(str(qp1['k1']).lower(), "qp_k1")

    def test_sequence_get_elements_s2(self):
        s2, idx = self._get_elems('s2')
        qp1 = s2['qp1:1']
        qp2 = s2['qp2:1']
        self.assertLess(idx['qp1:1'], idx['qp2:1'])
        self.assertAlmostEqual(qp1['at'], 0)
        self.assertAlmostEqual(qp2['at'], 1)
        self.assertAlmostEqual(qp1['l'], 1)
        self.assertAlmostEqual(qp2['l'], 2)
        self.assertAlmostEqual(float(qp1['k1']), 3)
        self.assertAlmostEqual(float(qp2['k1']), 2)

    # def test_sequence_get_expanded_elements(self):

    def test_crash(self):
        """Check that a RuntimeError is raised in case MAD-X crashes."""
        # a.t.m. MAD-X crashes on this input, because the L (length)
        # parametere is missing:
        self.assertRaises(RuntimeError, self.mad.input, 'XXX: sequence;')

if __name__ == '__main__':
    unittest.main()
