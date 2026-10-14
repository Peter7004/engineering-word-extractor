import csv
import hashlib
import io
import re
from collections import Counter
from pathlib import Path

import pymupdf
import streamlit as st

BASE = Path(__file__).resolve().parent
STOPWORDS = set('a an the and or but if then of in on at to from for with by as is are was were be been being it its this that these those we you they he she i our their your not no do does did have has had can could may might will would shall should also than such into about between through during each which who where when how all any both more most other some there here only very using used use'.split())


def normalize(text):
    text = text.replace('\u00ad', '')
    text = re.sub(r'([A-Za-z])-\s*\r?\n\s*([A-Za-z])', r'\1\2', text)
    return re.sub(r'\s+', ' ', text).strip().lower()


def load_dictionary(paths):
    terms, warnings = {}, []
    for path in paths:
        try:
            with path.open(encoding='utf-8-sig', newline='') as file:
                reader = csv.DictReader(file)
                if reader.fieldnames != ['term', 'meaning']:
                    raise ValueError('헤더는 term,meaning이어야 합니다.')
                for line, row in enumerate(reader, 2):
                    if None in row or row.get('meaning') is None:
                        raise ValueError(f'{line}행의 열 개수가 올바르지 않습니다.')
                    term = normalize(row['term'])
                    meaning = row['meaning'].strip()
                    if not term or not meaning:
                        warnings.append(f'{path.name} {line}행: 빈 용어 또는 뜻을 건너뛰었습니다.')
                        continue
                    if term in terms and terms[term] != meaning:
                        warnings.append(f'뜻 충돌: {term} — 먼저 읽은 뜻 “{terms[term]}”을 사용합니다 ({path.name}).')
                    else:
                        terms[term] = meaning
        except (OSError, UnicodeError, csv.Error, ValueError) as exc:
            raise ValueError(f'사전 {path.name}을 읽을 수 없습니다: {exc}') from exc
    return terms, warnings


def extract_pdf(data):
    try:
        with pymupdf.open(stream=data, filetype='pdf') as doc:
            if doc.needs_pass:
                raise ValueError('암호로 보호된 PDF입니다. 암호를 해제한 파일을 사용해 주세요.')
            pages = [page.get_text() for page in doc]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('PDF를 읽을 수 없습니다. 손상 여부와 파일 형식을 확인해 주세요.') from exc
    if not any(page.strip() for page in pages):
        raise ValueError('추출할 텍스트가 없습니다. 빈 PDF 또는 스캔 PDF일 수 있습니다. OCR은 지원하지 않습니다.')
    # Normalize pages separately so words do not join across page boundaries.
    return ' '.join(normalize(page) for page in pages), len(pages), sum(not page.strip() for page in pages)


def analyze(text, terms):
    text = normalize(text)
    occupied = bytearray(len(text))
    known = Counter()
    for term in sorted(terms, key=lambda t: (-len(t.split()), -len(t), t)):
        pattern = r'(?<![\w])' + re.escape(term) + r'(?![\w])'
        for match in re.finditer(pattern, text):
            start, end = match.span()
            if not any(occupied[start:end]):
                known[term] += 1
                occupied[start:end] = b'\x01' * (end - start)
    remainder = ''.join(' ' if occupied[i] else char for i, char in enumerate(text))
    candidates = Counter(word for word in re.findall(r'(?<![\w])[a-z]+(?:[-\'][a-z]+)*(?![\w])', remainder)
                         if len(word) > 1 and word not in STOPWORDS and word not in terms)
    return dict(known), dict(candidates)


def export_csv(selected, counts):
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    unique = {normalize(term) for term in selected if normalize(term) in counts}
    for term in sorted(unique, key=lambda t: (-counts[t], t)):
        writer.writerow([term])
    return output.getvalue().encode('utf-8-sig')


def reset_result(state, signature):
    if state.get('signature') != signature:
        for key in list(state):
            if key in ('result', 'selected') or key.startswith('word_'):
                del state[key]
        state['signature'] = signature


def render_words(kind, counts, meanings):
    query = st.text_input('단어 검색', key=f'search_{kind}').strip().lower()
    minimum = st.number_input('최소 등장 횟수', min_value=1, value=1, step=1, key=f'min_{kind}')
    visible = sorted((t for t, n in counts.items() if n >= minimum and query in t), key=lambda t: (-counts[t], t))
    left, right = st.columns(2)
    select_all = left.button('표시된 단어 전체 선택', key=f'all_{kind}')
    clear_all = right.button('표시된 단어 선택 해제', key=f'none_{kind}')
    selected = st.session_state['selected']
    if select_all or clear_all:
        for term in visible:
            selected[term] = select_all
            st.session_state[f'word_{kind}_{term}'] = select_all
    st.caption(f'표시 {len(visible)}개 / 전체 {len(counts)}개 · 전체 선택/해제는 현재 검색·필터에 표시된 단어에 적용됩니다.')
    for term in visible:
        key = f'word_{kind}_{term}'
        if key not in st.session_state:
            st.session_state[key] = selected.get(term, kind == 'known')
        label = f'{term} — {counts[term]}회'
        if term in meanings:
            label += f' · {meanings[term]}'
        selected[term] = st.checkbox(label, key=key)
    if not visible:
        st.info('조건에 맞는 단어가 없습니다.')


def main():
    st.set_page_config(page_title='Engineering Word Extractor', layout='wide')
    st.title('Engineering Word Extractor')
    st.write('영문 공학 PDF에서 단어를 추출하고 검토한 뒤 단일 열 CSV로 저장합니다.')
    electrical = st.checkbox('전기공학', value=True)
    semiconductor = st.checkbox('반도체공정', value=False)
    upload = st.file_uploader('영문 PDF 업로드', type=['pdf'])
    paths = [BASE / 'dictionaries' / name for enabled, name in [(electrical, 'electrical.csv'), (semiconductor, 'semiconductor.csv')] if enabled]
    data = upload.getvalue() if upload else b''
    try:
        fingerprints = tuple((str(p), hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else 'missing') for p in paths)
    except OSError:
        reset_result(st.session_state, None)
        st.error('사전 파일에 접근할 수 없습니다. 파일 권한을 확인해 주세요.')
        return
    signature = (hashlib.sha256(data).hexdigest(), fingerprints)
    reset_result(st.session_state, signature)
    if st.button('분석 실행', type='primary'):
        st.session_state.pop('result', None)
        if not paths:
            st.warning('전문 분야를 하나 이상 선택해 주세요.')
        elif not upload:
            st.warning('PDF 파일을 업로드해 주세요.')
        else:
            try:
                terms, warnings = load_dictionary(paths)
                with st.spinner('PDF를 분석하고 있습니다...'):
                    text, pages, empty = extract_pdf(data)
                    known, candidates = analyze(text, terms)
                st.session_state['result'] = (known, candidates, terms, pages, empty, warnings)
                st.session_state['selected'] = {**{t: True for t in known}, **{t: False for t in candidates}}
                for key in list(st.session_state):
                    if key.startswith('word_'):
                        del st.session_state[key]
            except ValueError as exc:
                st.error(str(exc))
    if 'result' not in st.session_state:
        return
    known, candidates, terms, pages, empty, warnings = st.session_state['result']
    for warning in warnings:
        st.warning(warning)
    if empty:
        st.warning(f'{empty}개 페이지에는 추출 가능한 텍스트가 없습니다. 해당 페이지 내용은 결과에 포함되지 않습니다.')
    st.success(f'{pages}페이지 분석 완료 · 전문 용어 {len(known)}개 · 신규 후보 {len(candidates)}개')
    known_tab, candidate_tab = st.tabs(['기존 전문 용어', '신규 단어 후보'])
    with known_tab:
        render_words('known', known, terms)
    with candidate_tab:
        st.caption('사전에 없는 단어 후보입니다. 전문 용어 여부를 직접 검토해 주세요.')
        render_words('candidate', candidates, {})
    selected = [t for t, enabled in st.session_state['selected'].items() if enabled]
    st.write(f'선택한 단어: {len(selected)}개')
    st.download_button('CSV 다운로드', export_csv(selected, {**known, **candidates}),
                       file_name='extracted_words.csv', mime='text/csv', disabled=not selected)


if __name__ == '__main__':
    main()
