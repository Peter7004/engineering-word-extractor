import csv
import io
import tempfile
import unittest
from pathlib import Path

import pymupdf
from streamlit.testing.v1 import AppTest
import app


class CoreTests(unittest.TestCase):
    def test_domains(self):
        electrical, _ = app.load_dictionary([app.BASE / 'dictionaries/electrical.csv'])
        semiconductor, _ = app.load_dictionary([app.BASE / 'dictionaries/semiconductor.csv'])
        both, _ = app.load_dictionary([app.BASE / 'dictionaries/electrical.csv', app.BASE / 'dictionaries/semiconductor.csv'])
        self.assertNotIn('etching', electrical)
        self.assertNotIn('voltage', semiconductor)
        known, _ = app.analyze('voltage etching semiconductor semiconductor', both)
        self.assertEqual(known, {'voltage': 1, 'etching': 1, 'semiconductor': 2})

    def test_overlap_and_candidates(self):
        known, new = app.analyze('Power factor correction. power factor. current concurrent. Novel novel and the.',
                                 {'power factor correction': '보정', 'power factor': '역률', 'current': '전류'})
        self.assertEqual(known, {'power factor correction': 1, 'power factor': 1, 'current': 1})
        self.assertEqual(new, {'concurrent': 1, 'novel': 2})
        self.assertEqual(app.normalize('Semi-\nconductor\n  VOLTAGE'), 'semiconductor voltage')

    def test_dictionary_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'test.csv'
            with self.assertRaises(ValueError):
                app.load_dictionary([path])
            path.write_text('bad,header\nx,y\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                app.load_dictionary([path])
            path.write_text('term,meaning\n Voltage ,전압\nvoltage,다른 뜻\n', encoding='utf-8-sig')
            terms, warnings = app.load_dictionary([path])
            self.assertEqual(terms, {'voltage': '전압'})
            self.assertEqual(len(warnings), 1)

    def test_pdf(self):
        with pymupdf.open() as doc:
            doc.new_page().insert_text((72, 72), 'Voltage current')
            doc.new_page().insert_text((72, 72), 'Etching')
            text, pages, empty = app.extract_pdf(doc.tobytes())
            self.assertEqual(pages, 2)
            self.assertEqual(empty, 0)
            self.assertIn('etching', text)
        with pymupdf.open() as doc:
            doc.new_page()
            with self.assertRaises(ValueError):
                app.extract_pdf(doc.tobytes())
        for data in (b'', b'broken PDF'):
            with self.assertRaises(ValueError):
                app.extract_pdf(data)

    def test_csv(self):
        data = app.export_csv(['Voltage', 'voltage', 'power factor', 'etching'], {'voltage': 2, 'power factor': 1, 'etching': 1})
        self.assertTrue(data.startswith(b'\xef\xbb\xbf'))
        self.assertEqual(list(csv.reader(io.StringIO(data.decode('utf-8-sig')))), [['voltage'], ['etching'], ['power factor']])

    def test_reset(self):
        state = {'signature': 'a', 'result': 1, 'selected': {'x': True}, 'word_known_x': True}
        app.reset_result(state, 'a')
        self.assertIn('result', state)
        app.reset_result(state, 'b')
        self.assertEqual(state, {'signature': 'b'})


class UITests(unittest.TestCase):
    def test_selection_filters(self):
        script = """import streamlit as st
from app import render_words
if 'selected' not in st.session_state:
    st.session_state['selected'] = {'voltage': True, 'current': True}
render_words('known', {'voltage': 3, 'current': 1}, {'voltage': '전압', 'current': '전류'})
"""
        at = AppTest.from_string(script).run()
        self.assertFalse(at.exception)
        at.checkbox[0].uncheck().run()
        at.text_input[0].set_value('current').run()
        self.assertFalse(at.session_state['selected']['voltage'])
        at.button[1].click().run()
        self.assertFalse(at.session_state['selected']['current'])
        at.button[0].click().run()
        self.assertTrue(at.session_state['selected']['current'])
        at.text_input[0].set_value('').run()
        at.number_input[0].set_value(2).run()
        self.assertFalse(at.checkbox[0].value)
        self.assertTrue(at.session_state['selected']['current'])
        self.assertFalse(at.exception)

    def test_no_input(self):
        at = AppTest.from_file(str(app.BASE / 'app.py')).run()
        at.button[0].click().run()
        self.assertIn('PDF', at.warning[0].value)
        at.checkbox[0].uncheck().run()
        at.button[0].click().run()
        self.assertIn('분야', at.warning[0].value)
        self.assertFalse(at.exception)


if __name__ == '__main__':
    unittest.main()
