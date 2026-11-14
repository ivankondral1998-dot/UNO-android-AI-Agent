#!/usr/bin/env python3
"""Host SQL contract fault-injection against EXACT AndroidOutcomeStore CREATE_* strings.
Does not execute Android Kotlin; Android build and device gates remain open.
"""
import hashlib
import re
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KOTLIN = ROOT / 'app/src/main/kotlin/org/unovyra/uno/AndroidOutcomeStore.kt'
SOURCE = KOTLIN.read_text(encoding='utf-8')
SQL_NAMES = ['OPERATIONS', 'MEMORY', 'REFERENCE_INDEX', 'TRUSTED_LINK']
SCHEMA = {}
for name in SQL_NAMES:
    match = re.search(r'internal const val CREATE_' + name + r'\s*=\s*"""(.*?)"""', SOURCE, re.S)
    assert match, f'missing CREATE_{name}'
    SCHEMA[name] = match.group(1).strip()

assert 'setWriteAheadLoggingEnabled(true)' in SOURCE
assert 'db.beginTransactionNonExclusive()' in SOURCE
assert 'db.setTransactionSuccessful()' in SOURCE
assert SOURCE.find('db.endTransaction()') > SOURCE.find('db.setTransactionSuccessful()')
assert 'failed = true' in SOURCE and 'onUpgrade(' in SOURCE
assert 'executable=false' in SOURCE
assert 'stopLatch' in SOURCE

PASS = 0

def test(name, fn):
    global PASS
    fn()
    PASS += 1
    print(f'PASS SQL_TXN {name}')

with tempfile.TemporaryDirectory(prefix='uno-sqlite-host-') as tmp:
    path = str(Path(tmp) / 'outcome.db')
    conn = sqlite3.connect(path, isolation_level=None)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    for sql in SCHEMA.values():
        conn.execute(sql)
    sha = 'a' * 64
    ticket = 'session1:0:1'
    payload = b'REFERENCE_READBACK_CLAIM/1|ticket|TRUE|READBACK_LOCAL|1|5'
    digest = hashlib.sha256(payload).hexdigest()

    def prepared(id=ticket, session='session1'):
        conn.execute('INSERT INTO operations(ticket_id,proposal_sha256,session_nonce,owner_epoch,deadline_ns,prepared_ns,phase,used) VALUES(?,?,?,?,?,?,1,0)',
                     (id, sha, session, 0, 100, 1))

    def arm(id=ticket):
        conn.execute('UPDATE operations SET phase=2,dispatch_ns=5 WHERE ticket_id=? AND session_nonce=? AND phase=1 AND used=0', (id, 'session1'))
        return conn.execute('SELECT changes()').fetchone()[0]

    def commit_claim(id=ticket, t=6):
        conn.execute('INSERT OR IGNORE INTO memory_records(content_sha256,kind,payload) VALUES(?,?,?)', (digest,'REFERENCE_READBACK_CLAIM',payload))
        conn.execute('UPDATE operations SET phase=3,used=1,outcome=1,source_tag=?,generation=1,observed_ns=?,memory_ref=? WHERE ticket_id=? AND phase=2 AND used=0',
                     ('READBACK_LOCAL',t,digest,id))
        return conn.execute('SELECT changes()').fetchone()[0]

    test('schema opens with FK, WAL and integrity', lambda: (
        None if conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok' and
        conn.execute('PRAGMA foreign_keys').fetchone()[0] == 1 else (_ for _ in ()).throw(AssertionError())))

    test('stage and arm are separate durable phases', lambda: (
        prepared(),
        None if arm() == 1 and conn.execute('SELECT phase,used FROM operations WHERE ticket_id=?',(ticket,)).fetchone()==(2,0) else (_ for _ in ()).throw(AssertionError())))

    def do_success():
        conn.execute('BEGIN IMMEDIATE')
        assert commit_claim() == 1
        conn.commit()
        assert conn.execute('SELECT phase,used,outcome,memory_ref FROM operations WHERE ticket_id=?',(ticket,)).fetchone()==(3,1,1,digest)
        assert conn.execute('SELECT payload FROM memory_records WHERE content_sha256=?',(digest,)).fetchone()[0] == payload
    test('atomic used + outcome + memory reference', do_success)

    def replay():
        conn.close()
        c = sqlite3.connect(path)
        assert c.execute('SELECT phase,used FROM operations WHERE ticket_id=?',(ticket,)).fetchone() == (3,1)
        assert c.execute('SELECT count(*) FROM operations WHERE phase!=3').fetchone()[0] == 0
        c.close()
    # reconnect because test uses the writable connection later
    test('committed row survives reopen', lambda: (
        None if sqlite3.connect(path).execute('SELECT used FROM operations WHERE ticket_id=?',(ticket,)).fetchone()[0] == 1 else (_ for _ in ()).throw(AssertionError())))

    def duplicate():
        try: prepared()
        except sqlite3.IntegrityError: return
        raise AssertionError('duplicate accepted')
    test('duplicate id cannot stage again', duplicate)

    test('used prevents duplicate arm', lambda: (None if arm() == 0 else (_ for _ in ()).throw(AssertionError())))

    def no_missing_memory():
        prepared('missing');arm('missing')
        try:
            conn.execute("UPDATE operations SET phase=3,used=1,outcome=1,source_tag='S',generation=1,observed_ns=6,memory_ref=? WHERE ticket_id='missing'", ('f'*64,))
        except sqlite3.IntegrityError: return
        raise AssertionError('unknown memory ref accepted')
    test('memory ref must point at existing content', no_missing_memory)

    def no_split_status():
        try:conn.execute("UPDATE operations SET used=1 WHERE ticket_id='missing'")
        except sqlite3.IntegrityError: return
        raise AssertionError('used without receipt accepted')
    test('used without readback is rejected',no_split_status)

    def rollback_injected():
        prepared('rollback');arm('rollback')
        conn.execute('BEGIN IMMEDIATE')
        assert commit_claim('rollback') == 1
        conn.rollback()  # simulated crash before COMMIT
        assert conn.execute("SELECT phase,used,memory_ref FROM operations WHERE ticket_id='rollback'").fetchone()==(2,0,None)
    test('rollback after all writes leaves no half-commit',rollback_injected)

    def rollback_midway():
        prepared('midway');arm('midway')
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('INSERT OR IGNORE INTO memory_records(content_sha256,kind,payload) VALUES (?,?,?)',('b'*64,'REFERENCE_READBACK_CLAIM',b'midway'))
        conn.rollback()
        assert conn.execute("SELECT count(*) FROM memory_records WHERE content_sha256=?",('b'*64,)).fetchone()[0] == 0
        assert conn.execute("SELECT used FROM operations WHERE ticket_id='midway'").fetchone()[0]==0
    test('rollback before update leaves no orphan memory',rollback_midway)

    def pre_dispatch_denial():
        prepared('prestop')
        try:conn.execute("UPDATE operations SET phase=3,used=1 WHERE ticket_id='prestop'")
        except sqlite3.IntegrityError: pass
        else:raise AssertionError('pretend dispatch success accepted')
        assert conn.execute("SELECT phase,used FROM operations WHERE ticket_id='prestop'").fetchone()==(1,0)
    test('prepared cannot be upgraded directly to terminal without evidence',pre_dispatch_denial)

    def stale_readback_sql():
        prepared('stale');arm('stale')
        try:commit_claim('stale',4)
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('stale timestamp accepted')
        assert conn.execute("SELECT phase,used FROM operations WHERE ticket_id='stale'").fetchone()==(2,0)
    test('terminal timestamp cannot predate dispatch',stale_readback_sql)

    def prevent_memory_delete():
        try:conn.execute('DELETE FROM memory_records WHERE content_sha256=?',(digest,))
        except sqlite3.IntegrityError:return
        raise AssertionError('referenced memory deleted')
    test('committed memory cannot be deleted while referenced',prevent_memory_delete)

    def inspect_only():
        c=sqlite3.connect(path)
        entries=c.execute('SELECT ticket_id,phase,used,outcome,memory_ref FROM operations').fetchall()
        assert len(entries)>=5
        assert any(phase==2 and used==0 for _,phase,used,*_ in entries)
        c.close()
    test('incomplete records persist for reconciliation not retry',inspect_only)

    conn.close()
print(f'UNO_SQLITE_SCHEMA_HOST_PASS={PASS}')
