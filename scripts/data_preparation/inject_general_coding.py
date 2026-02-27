"""
Ouroboros AI - General Coding Data Injector  (Task 2.2)
========================================================
Mixes 5–10% of high-quality general coding tasks into the training split to
prevent catastrophic forgetting of Qwen Coder 3B's baseline syntax generation.

Design decisions
----------------
* Only `train.jsonl` is modified — val/test stay pure security data.
* Uses a neutral system prompt ("You are an expert software engineer…") that
  is intentionally different from the security agent prompt, so the model
  retains the ability to switch contexts.
* Content-hash deduplication makes re-runs idempotent.
* Optional: downloads CodeAlpaca-20k from HuggingFace if `datasets` is
  installed; falls back gracefully to the built-in corpus otherwise.

Usage
-----
  # Default: inject 8% general data into train.jsonl
  python scripts/data_preparation/inject_general_coding.py

  # Custom ratio (10%)
  python scripts/data_preparation/inject_general_coding.py --ratio 0.10

  # Use HuggingFace CodeAlpaca dataset (requires: pip install datasets)
  python scripts/data_preparation/inject_general_coding.py --source codealp

  # Custom paths
  python scripts/data_preparation/inject_general_coding.py \\
      --train-file data/splits/train.jsonl --ratio 0.08

  # Dry-run: print stats without modifying the file
  python scripts/data_preparation/inject_general_coding.py --dry-run
"""

import argparse
import hashlib
import json
import logging
import math
import random
import sys
from pathlib import Path
from typing import Dict, Generator, List, Optional, Set

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("inject_general_coding")

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

GENERAL_SYSTEM_PROMPT = (
    "You are an expert software engineer. Write clean, correct, well-documented code "
    "that solves the given problem. Follow best practices for the language used."
)

# ─────────────────────────────────────────────────────────────────────────────
# BUILT-IN GENERAL CODING CORPUS
# Each tuple: (instruction, language, solution)
# Covers: algorithms, data structures, OOP, I/O, async, testing, many languages
# ─────────────────────────────────────────────────────────────────────────────

_BUILTIN_TASKS = [
    # ── Python ──────────────────────────────────────────────────────────────
    (
        "Implement a binary search function in Python that returns the index of the target, or -1 if not found.",
        "Python",
        """\
def binary_search(arr: list, target: int) -> int:
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
""",
    ),
    (
        "Write a Python decorator that logs the execution time of any function.",
        "Python",
        """\
import time
import functools
import logging

logger = logging.getLogger(__name__)

def log_time(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f\"{func.__name__} completed in {elapsed:.4f}s\")
        return result
    return wrapper
""",
    ),
    (
        "Implement a thread-safe LRU cache in Python using collections.OrderedDict.",
        "Python",
        """\
import threading
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache: OrderedDict = OrderedDict()
        self.lock = threading.Lock()

    def get(self, key: int) -> int:
        with self.lock:
            if key not in self.cache:
                return -1
            self.cache.move_to_end(key)
            return self.cache[key]

    def put(self, key: int, value: int) -> None:
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
""",
    ),
    (
        "Write a Python context manager that temporarily changes the current working directory.",
        "Python",
        """\
import os
from contextlib import contextmanager

@contextmanager
def change_dir(path: str):
    original = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(original)

# Usage:
# with change_dir('/tmp'):
#     print(os.getcwd())  # /tmp
""",
    ),
    (
        "Implement merge sort in Python with type hints.",
        "Python",
        """\
from typing import List

def merge_sort(arr: List[int]) -> List[int]:
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left  = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return _merge(left, right)

def _merge(left: List[int], right: List[int]) -> List[int]:
    result, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    return result + left[i:] + right[j:]
""",
    ),
    (
        "Write an async Python function that fetches multiple URLs concurrently using asyncio and aiohttp.",
        "Python",
        """\
import asyncio
import aiohttp
from typing import List, Dict

async def fetch_all(urls: List[str]) -> Dict[str, str]:
    async def fetch_one(session: aiohttp.ClientSession, url: str) -> tuple:
        async with session.get(url) as resp:
            return url, await resp.text()

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_one(session, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {url: body for url, body in results if not isinstance(body, Exception)}
""",
    ),
    (
        "Implement a Python generator that yields chunks of a list of a given size.",
        "Python",
        """\
from typing import Generator, List, TypeVar
T = TypeVar('T')

def chunked(lst: List[T], size: int) -> Generator[List[T], None, None]:
    if size <= 0:
        raise ValueError(\"size must be positive\")
    for i in range(0, len(lst), size):
        yield lst[i: i + size]
""",
    ),
    (
        "Write a Python dataclass for a paginated API response including total count, page, and results list.",
        "Python",
        """\
from dataclasses import dataclass, field
from typing import Generic, List, TypeVar

T = TypeVar('T')

@dataclass
class PaginatedResponse(Generic[T]):
    items:       List[T]
    total:       int
    page:        int
    page_size:   int
    has_next:    bool = field(init=False)

    def __post_init__(self):
        self.has_next = (self.page * self.page_size) < self.total

    @property
    def total_pages(self) -> int:
        return -(-self.total // self.page_size)  # ceiling division
""",
    ),
    (
        "Implement Dijkstra's shortest-path algorithm in Python using a min-heap.",
        "Python",
        """\
import heapq
from typing import Dict, List, Tuple

def dijkstra(graph: Dict[int, List[Tuple[int,int]]], source: int) -> Dict[int, int]:
    dist = {source: 0}
    heap = [(0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, float('inf')):
            continue
        for v, w in graph.get(u, []):
            nd = d + w
            if nd < dist.get(v, float('inf')):
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist
""",
    ),
    (
        "Write Python unit tests for a stack implementation using unittest.",
        "Python",
        """\
import unittest

class Stack:
    def __init__(self): self._data = []
    def push(self, x): self._data.append(x)
    def pop(self): return self._data.pop()
    def peek(self): return self._data[-1]
    def is_empty(self): return not self._data
    def __len__(self): return len(self._data)

class TestStack(unittest.TestCase):
    def setUp(self):
        self.s = Stack()

    def test_push_pop(self):
        self.s.push(1); self.s.push(2)
        self.assertEqual(self.s.pop(), 2)

    def test_peek(self):
        self.s.push(42)
        self.assertEqual(self.s.peek(), 42)
        self.assertEqual(len(self.s), 1)

    def test_empty_pop(self):
        with self.assertRaises(IndexError):
            self.s.pop()

    def test_is_empty(self):
        self.assertTrue(self.s.is_empty())
        self.s.push(0)
        self.assertFalse(self.s.is_empty())

if __name__ == '__main__':
    unittest.main()
""",
    ),
    # ── JavaScript / TypeScript ─────────────────────────────────────────────
    (
        "Write a JavaScript function that deep-clones a plain object without using JSON.parse/stringify.",
        "JavaScript",
        """\
function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') return obj;
  if (obj instanceof Date)   return new Date(obj.getTime());
  if (obj instanceof Array)  return obj.map(deepClone);
  const clone = Object.create(Object.getPrototypeOf(obj));
  for (const key of Object.keys(obj)) {
    clone[key] = deepClone(obj[key]);
  }
  return clone;
}
""",
    ),
    (
        "Implement a debounce function in JavaScript with leading and trailing call support.",
        "JavaScript",
        """\
function debounce(fn, wait, { leading = false, trailing = true } = {}) {
  let timer = null;
  let lastArgs;

  return function (...args) {
    lastArgs = args;
    const callNow = leading && !timer;
    clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      if (trailing && !callNow) fn.apply(this, lastArgs);
    }, wait);
    if (callNow) fn.apply(this, args);
  };
}
""",
    ),
    (
        "Write a TypeScript generic function that groups an array of objects by a key.",
        "TypeScript",
        """\
function groupBy<T, K extends keyof T>(items: T[], key: K): Map<T[K], T[]> {
  const map = new Map<T[K], T[]>();
  for (const item of items) {
    const k = item[key];
    if (!map.has(k)) map.set(k, []);
    map.get(k)!.push(item);
  }
  return map;
}

// Example:
// const users = [{ role: 'admin', name: 'Alice' }, { role: 'user', name: 'Bob' }];
// groupBy(users, 'role') // Map { 'admin' => [...], 'user' => [...] }
""",
    ),
    (
        "Implement a Promise.allSettled polyfill in JavaScript.",
        "JavaScript",
        """\
if (!Promise.allSettled) {
  Promise.allSettled = function (promises) {
    return Promise.all(
      promises.map(p =>
        Promise.resolve(p).then(
          value  => ({ status: 'fulfilled', value }),
          reason => ({ status: 'rejected',  reason })
        )
      )
    );
  };
}
""",
    ),
    (
        "Write an Express.js middleware that rate-limits requests per IP using an in-memory store.",
        "JavaScript",
        """\
const rateLimit = (maxRequests, windowMs) => {
  const store = new Map(); // ip -> { count, reset }

  return (req, res, next) => {
    const ip  = req.ip;
    const now = Date.now();
    let   rec = store.get(ip);

    if (!rec || now > rec.reset) {
      rec = { count: 1, reset: now + windowMs };
    } else {
      rec.count += 1;
    }
    store.set(ip, rec);

    if (rec.count > maxRequests) {
      return res.status(429).json({ error: 'Too many requests' });
    }
    next();
  };
};

module.exports = rateLimit;
""",
    ),
    # ── Java ────────────────────────────────────────────────────────────────
    (
        "Implement a generic Pair class in Java with equals, hashCode, and toString.",
        "Java",
        """\
import java.util.Objects;

public final class Pair<A, B> {
    public final A first;
    public final B second;

    public Pair(A first, B second) {
        this.first  = first;
        this.second = second;
    }

    public static <A, B> Pair<A, B> of(A a, B b) { return new Pair<>(a, b); }

    @Override public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Pair<?,?> p)) return false;
        return Objects.equals(first, p.first) && Objects.equals(second, p.second);
    }
    @Override public int hashCode() { return Objects.hash(first, second); }
    @Override public String toString() { return \"(\" + first + \", \" + second + \")\"; }
}
""",
    ),
    (
        "Write a Java method that finds all duplicate elements in an integer array using a HashSet.",
        "Java",
        """\
import java.util.HashSet;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

public static List<Integer> findDuplicates(int[] nums) {
    Set<Integer> seen = new HashSet<>();
    Set<Integer> dupes = new HashSet<>();
    for (int n : nums) {
        if (!seen.add(n)) dupes.add(n);
    }
    return new ArrayList<>(dupes);
}
""",
    ),
    (
        "Implement a Builder pattern in Java for constructing an HTTP request object.",
        "Java",
        """\
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public final class HttpRequest {
    private final String method;
    private final String url;
    private final Map<String, String> headers;
    private final String body;

    private HttpRequest(Builder b) {
        this.method  = b.method;
        this.url     = b.url;
        this.headers = Collections.unmodifiableMap(b.headers);
        this.body    = b.body;
    }

    public static class Builder {
        private String method = \"GET\";
        private final String url;
        private final Map<String, String> headers = new HashMap<>();
        private String body;

        public Builder(String url) { this.url = url; }
        public Builder method(String m)          { this.method = m; return this; }
        public Builder header(String k, String v){ headers.put(k, v); return this; }
        public Builder body(String b)            { this.body = b; return this; }
        public HttpRequest build()               { return new HttpRequest(this); }
    }
    // getters omitted for brevity
}
""",
    ),
    (
        "Write a Java stream pipeline that groups a list of Strings by their first character and counts each group.",
        "Java",
        """\
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public static Map<Character, Long> groupByFirstChar(List<String> words) {
    return words.stream()
        .filter(w -> !w.isEmpty())
        .collect(Collectors.groupingBy(
            w -> w.charAt(0),
            Collectors.counting()
        ));
}
""",
    ),
    # ── C / C++ ─────────────────────────────────────────────────────────────
    (
        "Implement a singly linked list in C with insert, delete, and print operations.",
        "C",
        """\
#include <stdio.h>
#include <stdlib.h>

typedef struct Node { int data; struct Node *next; } Node;

Node *insert(Node *head, int val) {
    Node *n = malloc(sizeof(Node));
    n->data = val; n->next = head;
    return n;
}

Node *delete_val(Node *head, int val) {
    Node dummy = {0, head};
    Node *prev = &dummy;
    while (prev->next) {
        if (prev->next->data == val) {
            Node *tmp = prev->next;
            prev->next = tmp->next;
            free(tmp);
            break;
        }
        prev = prev->next;
    }
    return dummy.next;
}

void print_list(const Node *head) {
    for (; head; head = head->next)
        printf(\"%d -> \", head->data);
    puts(\"NULL\");
}
""",
    ),
    (
        "Write a C++ RAII wrapper class for a FILE* that automatically closes the file on destruction.",
        "C++",
        """\
#include <cstdio>
#include <stdexcept>
#include <string>

class FileHandle {
public:
    explicit FileHandle(const std::string& path, const char* mode) {
        fp_ = std::fopen(path.c_str(), mode);
        if (!fp_) throw std::runtime_error(\"Cannot open: \" + path);
    }

    ~FileHandle() { if (fp_) std::fclose(fp_); }

    // Non-copyable, movable
    FileHandle(const FileHandle&) = delete;
    FileHandle& operator=(const FileHandle&) = delete;

    FileHandle(FileHandle&& other) noexcept : fp_(other.fp_) { other.fp_ = nullptr; }
    FileHandle& operator=(FileHandle&&) = delete;

    FILE* get() const noexcept { return fp_; }

private:
    FILE* fp_ = nullptr;
};
""",
    ),
    (
        "Implement a hash map in C using open addressing with linear probing.",
        "C",
        """\
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define CAPACITY 64

typedef struct { char *key; int value; } Entry;
typedef struct { Entry *buckets; size_t capacity; size_t size; } HashMap;

static uint32_t fnv1a(const char *s) {
    uint32_t h = 2166136261u;
    while (*s) h = (h ^ (uint8_t)*s++) * 16777619u;
    return h;
}

HashMap *hm_create() {
    HashMap *m = calloc(1, sizeof(HashMap));
    m->capacity = CAPACITY;
    m->buckets  = calloc(CAPACITY, sizeof(Entry));
    return m;
}

void hm_put(HashMap *m, const char *key, int value) {
    size_t idx = fnv1a(key) % m->capacity;
    while (m->buckets[idx].key && strcmp(m->buckets[idx].key, key) != 0)
        idx = (idx + 1) % m->capacity;
    if (!m->buckets[idx].key) { m->buckets[idx].key = strdup(key); m->size++; }
    m->buckets[idx].value = value;
}

int hm_get(const HashMap *m, const char *key, int def) {
    size_t idx = fnv1a(key) % m->capacity;
    while (m->buckets[idx].key) {
        if (strcmp(m->buckets[idx].key, key) == 0) return m->buckets[idx].value;
        idx = (idx + 1) % m->capacity;
    }
    return def;
}
""",
    ),
    (
        "Write a C++ template function that finds the minimum and maximum elements of a vector simultaneously.",
        "C++",
        """\
#include <vector>
#include <stdexcept>
#include <utility>
#include <limits>

template<typename T>
std::pair<T, T> minmax_element(const std::vector<T>& v) {
    if (v.empty()) throw std::invalid_argument(\"empty vector\");
    T lo = v[0], hi = v[0];
    for (size_t i = 1; i + 1 < v.size(); i += 2) {
        if (v[i] < v[i+1]) { lo = std::min(lo, v[i]); hi = std::max(hi, v[i+1]); }
        else                { lo = std::min(lo, v[i+1]); hi = std::max(hi, v[i]); }
    }
    if (v.size() % 2 == 0) {
        lo = std::min(lo, v.back()); hi = std::max(hi, v.back());
    }
    return {lo, hi};
}
""",
    ),
    # ── Go ──────────────────────────────────────────────────────────────────
    (
        "Implement a concurrent worker pool in Go that processes tasks from a channel.",
        "Go",
        """\
package main

import (
    \"sync\"
)

type Task func()

type WorkerPool struct {
    tasks   chan Task
    wg      sync.WaitGroup
    workers int
}

func NewWorkerPool(workers, queueSize int) *WorkerPool {
    p := &WorkerPool{tasks: make(chan Task, queueSize), workers: workers}
    for i := 0; i < workers; i++ {
        p.wg.Add(1)
        go func() {
            defer p.wg.Done()
            for task := range p.tasks {
                task()
            }
        }()
    }
    return p
}

func (p *WorkerPool) Submit(t Task) { p.tasks <- t }
func (p *WorkerPool) Close() { close(p.tasks); p.wg.Wait() }
""",
    ),
    (
        "Write a Go function that reads a JSON file into a struct and returns it.",
        "Go",
        """\
package main

import (
    \"encoding/json\"
    \"fmt\"
    \"os\"
)

func ReadJSON[T any](path string) (T, error) {
    var result T
    f, err := os.Open(path)
    if err != nil { return result, fmt.Errorf(\"open: %w\", err) }
    defer f.Close()
    if err := json.NewDecoder(f).Decode(&result); err != nil {
        return result, fmt.Errorf(\"decode: %w\", err)
    }
    return result, nil
}
""",
    ),
    (
        "Implement a Go middleware that adds request ID and timing headers to HTTP responses.",
        "Go",
        """\
package middleware

import (
    \"net/http\"
    \"time\"

    \"github.com/google/uuid\"
)

func RequestID(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        id := uuid.New().String()
        w.Header().Set(\"X-Request-Id\", id)
        start := time.Now()
        next.ServeHTTP(w, r)
        w.Header().Set(\"X-Response-Time\", time.Since(start).String())
    })
}
""",
    ),
    # ── Rust ─────────────────────────────────────────────────────────────────
    (
        "Implement a stack data structure in Rust using a Vec, with push, pop, and peek methods.",
        "Rust",
        """\
pub struct Stack<T> {
    data: Vec<T>,
}

impl<T> Stack<T> {
    pub fn new() -> Self { Self { data: Vec::new() } }
    pub fn push(&mut self, item: T) { self.data.push(item); }
    pub fn pop(&mut self) -> Option<T> { self.data.pop() }
    pub fn peek(&self) -> Option<&T> { self.data.last() }
    pub fn is_empty(&self) -> bool { self.data.is_empty() }
    pub fn len(&self) -> usize { self.data.len() }
}

impl<T> Default for Stack<T> { fn default() -> Self { Self::new() } }
""",
    ),
    (
        "Write a Rust function that counts word frequencies in a string using a HashMap.",
        "Rust",
        """\
use std::collections::HashMap;

pub fn word_frequencies(text: &str) -> HashMap<String, usize> {
    let mut map = HashMap::new();
    for word in text.split_whitespace() {
        let clean: String = word.chars()
            .filter(|c| c.is_alphabetic())
            .collect::<String>()
            .to_lowercase();
        if !clean.is_empty() {
            *map.entry(clean).or_insert(0) += 1;
        }
    }
    map
}
""",
    ),
    (
        "Implement a Rust struct for a thread-safe counter using Arc and Mutex.",
        "Rust",
        """\
use std::sync::{Arc, Mutex};

#[derive(Clone)]
pub struct Counter {
    value: Arc<Mutex<i64>>,
}

impl Counter {
    pub fn new() -> Self { Self { value: Arc::new(Mutex::new(0)) } }
    pub fn increment(&self) { *self.value.lock().unwrap() += 1; }
    pub fn decrement(&self) { *self.value.lock().unwrap() -= 1; }
    pub fn get(&self) -> i64 { *self.value.lock().unwrap() }
    pub fn reset(&self) { *self.value.lock().unwrap() = 0; }
}
""",
    ),
    # ── SQL ─────────────────────────────────────────────────────────────────
    (
        "Write a SQL query to find the top 5 customers by total purchase amount, including ties.",
        "SQL",
        """\
WITH ranked AS (
    SELECT
        c.customer_id,
        c.name,
        SUM(o.amount)  AS total_spent,
        DENSE_RANK() OVER (ORDER BY SUM(o.amount) DESC) AS rnk
    FROM customers c
    JOIN orders o USING (customer_id)
    GROUP BY c.customer_id, c.name
)
SELECT customer_id, name, total_spent
FROM   ranked
WHERE  rnk <= 5
ORDER  BY rnk, name;
""",
    ),
    (
        "Write a SQL query that detects duplicate email addresses in a users table.",
        "SQL",
        """\
SELECT
    email,
    COUNT(*) AS occurrences,
    STRING_AGG(CAST(user_id AS VARCHAR), ', ') AS user_ids
FROM users
GROUP BY email
HAVING COUNT(*) > 1
ORDER BY occurrences DESC;
""",
    ),
    (
        "Write a SQL stored procedure that inserts a new order and updates inventory atomically.",
        "SQL",
        """\
CREATE OR REPLACE PROCEDURE place_order(
    p_customer_id INT,
    p_product_id  INT,
    p_quantity    INT
)
LANGUAGE plpgsql AS $$
BEGIN
    -- Verify stock
    IF (SELECT stock FROM products WHERE id = p_product_id) < p_quantity THEN
        RAISE EXCEPTION 'Insufficient stock for product %', p_product_id;
    END IF;

    INSERT INTO orders (customer_id, product_id, quantity, created_at)
    VALUES (p_customer_id, p_product_id, p_quantity, NOW());

    UPDATE products
    SET stock = stock - p_quantity
    WHERE id = p_product_id;

    COMMIT;
END;
$$;
""",
    ),
    # ── Bash / Shell ─────────────────────────────────────────────────────────
    (
        "Write a Bash script that backs up a directory to a timestamped tarball and removes backups older than 7 days.",
        "Bash",
        """\
#!/usr/bin/env bash
set -euo pipefail

SRC_DIR=\"${1:?Usage: $0 <source-dir> [backup-dir]}\"
BACKUP_DIR=\"${2:-/var/backups}\"
STAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE=\"${BACKUP_DIR}/backup_${STAMP}.tar.gz\"

mkdir -p \"$BACKUP_DIR\"
tar -czf \"$ARCHIVE\" -C \"$(dirname \"$SRC_DIR\")\" \"$(basename \"$SRC_DIR\")\"
echo \"Created: $ARCHIVE\"

# Remove backups older than 7 days
find \"$BACKUP_DIR\" -name 'backup_*.tar.gz' -mtime +7 -print -delete
""",
    ),
    (
        "Write a Bash function that retries a command up to N times with exponential backoff.",
        "Bash",
        """\
#!/usr/bin/env bash

retry() {
    local max=\"${1}\"; shift
    local delay=1
    local attempt=1

    while true; do
        \"$@\" && return 0
        if (( attempt >= max )); then
            echo \"[retry] Command failed after $max attempts: $*\" >&2
            return 1
        fi
        echo \"[retry] Attempt $attempt/$max failed. Retrying in ${delay}s…\" >&2
        sleep \"$delay\"
        (( delay *= 2 ))
        (( attempt++ ))
    done
}

# Usage: retry 5 curl -sSf https://example.com
""",
    ),
    # ── Dockerfile ─────────────────────────────────────────────────────────
    (
        "Write a multi-stage Dockerfile for a Python FastAPI application with a minimal production image.",
        "Dockerfile",
        """\
# ── Build stage ───────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Production stage ──────────────────────────────────────────────────
FROM python:3.12-slim AS production

# Drop root — create non-privileged user
RUN useradd -r -u 1001 -s /sbin/nologin appuser

WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \\
    CMD python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\"

CMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]
""",
    ),
    # ── Algorithms / Data structures ────────────────────────────────────────
    (
        "Implement a Trie (prefix tree) in Python supporting insert, search, and startsWith.",
        "Python",
        """\
class TrieNode:
    __slots__ = ('children', 'is_end')
    def __init__(self):
        self.children: dict[str, 'TrieNode'] = {}
        self.is_end = False

class Trie:
    def __init__(self): self.root = TrieNode()

    def insert(self, word: str) -> None:
        node = self.root
        for ch in word:
            node = node.children.setdefault(ch, TrieNode())
        node.is_end = True

    def search(self, word: str) -> bool:
        node = self._find(word)
        return node is not None and node.is_end

    def starts_with(self, prefix: str) -> bool:
        return self._find(prefix) is not None

    def _find(self, s: str):
        node = self.root
        for ch in s:
            node = node.children.get(ch)
            if node is None: return None
        return node
""",
    ),
    (
        "Implement a min-heap (priority queue) in Python from scratch without using heapq.",
        "Python",
        """\
class MinHeap:
    def __init__(self): self._h = []

    def push(self, val):
        self._h.append(val)
        self._sift_up(len(self._h) - 1)

    def pop(self):
        if not self._h: raise IndexError(\"pop from empty heap\")
        self._swap(0, len(self._h) - 1)
        val = self._h.pop()
        if self._h: self._sift_down(0)
        return val

    def peek(self): return self._h[0] if self._h else None
    def __len__(self): return len(self._h)

    def _sift_up(self, i):
        parent = (i - 1) // 2
        while i > 0 and self._h[i] < self._h[parent]:
            self._swap(i, parent); i = parent; parent = (i - 1) // 2

    def _sift_down(self, i):
        n = len(self._h)
        while True:
            smallest, l, r = i, 2*i+1, 2*i+2
            if l < n and self._h[l] < self._h[smallest]: smallest = l
            if r < n and self._h[r] < self._h[smallest]: smallest = r
            if smallest == i: break
            self._swap(i, smallest); i = smallest

    def _swap(self, i, j): self._h[i], self._h[j] = self._h[j], self._h[i]
""",
    ),
    (
        "Write a Python function that performs topological sort on a DAG using Kahn's algorithm.",
        "Python",
        """\
from collections import deque
from typing import Dict, List

def topological_sort(graph: Dict[int, List[int]]) -> List[int]:
    \"\"\"Kahn's BFS-based topological sort. Raises ValueError if cycle detected.\"\"\"\
    in_degree = {u: 0 for u in graph}
    for u in graph:
        for v in graph[u]:
            in_degree.setdefault(v, 0)
            in_degree[v] += 1

    queue = deque(u for u, d in in_degree.items() if d == 0)
    order = []

    while queue:
        u = queue.popleft()
        order.append(u)
        for v in graph.get(u, []):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    if len(order) != len(in_degree):
        raise ValueError(\"Graph has a cycle — topological sort not possible\")
    return order
""",
    ),
    (
        "Implement an iterator protocol in Python for a Range class that supports step.",
        "Python",
        """\
class Range:
    def __init__(self, start: int, stop: int, step: int = 1):
        if step == 0: raise ValueError(\"step cannot be zero\")
        self.start, self.stop, self.step = start, stop, step

    def __iter__(self): return _RangeIterator(self.start, self.stop, self.step)
    def __len__(self):
        raw = (self.stop - self.start + self.step - (1 if self.step>0 else -1)) // self.step
        return max(0, raw)
    def __contains__(self, value: int) -> bool:
        if self.step > 0: return self.start <= value < self.stop and (value-self.start)%self.step==0
        return self.stop < value <= self.start and (self.start-value)%(-self.step)==0

class _RangeIterator:
    def __init__(self, start, stop, step): self.cur, self.stop, self.step = start, stop, step
    def __iter__(self): return self
    def __next__(self):
        if (self.step > 0 and self.cur >= self.stop) or \\
           (self.step < 0 and self.cur <= self.stop): raise StopIteration
        val, self.cur = self.cur, self.cur + self.step
        return val
""",
    ),
    # ── Miscellaneous ────────────────────────────────────────────────────────
    (
        "Implement a Redis-based distributed lock in Python using the SET NX EX pattern.",
        "Python",
        """\
import uuid
import time
import redis

class RedisLock:
    def __init__(self, client: redis.Redis, name: str, timeout: int = 30):
        self.client  = client
        self.name    = f\"lock:{name}\"
        self.timeout = timeout
        self._token  = None

    def acquire(self, block: bool = True, retry_delay: float = 0.1) -> bool:
        token = str(uuid.uuid4())
        while True:
            if self.client.set(self.name, token, nx=True, ex=self.timeout):
                self._token = token
                return True
            if not block: return False
            time.sleep(retry_delay)

    def release(self) -> bool:
        # Atomic check-and-delete with Lua
        script = \"\"\"
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else return 0 end\"\"\"
        result = self.client.eval(script, 1, self.name, self._token or '')
        self._token = None
        return bool(result)

    def __enter__(self): self.acquire(); return self
    def __exit__(self, *_): self.release()
""",
    ),
    (
        "Write a Python class that implements the Observer design pattern.",
        "Python",
        """\
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List

class Event:
    def __init__(self, name: str, data=None):
        self.name, self.data = name, data

class Observer(ABC):
    @abstractmethod
    def on_event(self, event: Event) -> None: ...

class EventBus:
    def __init__(self):
        self._listeners: dict[str, List[Observer]] = {}

    def subscribe(self, event_name: str, observer: Observer) -> None:
        self._listeners.setdefault(event_name, []).append(observer)

    def unsubscribe(self, event_name: str, observer: Observer) -> None:
        if event_name in self._listeners:
            self._listeners[event_name].remove(observer)

    def publish(self, event: Event) -> None:
        for obs in self._listeners.get(event.name, []):
            obs.on_event(event)
""",
    ),
    (
        "Implement a CSV parser in Python that handles quoted fields with embedded commas and newlines.",
        "Python",
        """\
import csv
import io
from typing import List

def parse_csv(text: str, delimiter: str = ',') -> List[List[str]]:
    \"\"\"
    Parse CSV text handling RFC 4180: quoted fields, embedded commas,
    embedded newlines, and escaped quotes ('\"\"').
    \"\"\"
    rows = []
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    for row in reader:
        rows.append(row)
    return rows

# Example:
# parse_csv('name,desc\\n\"Alice\",\"loves \\\"Python\\\"\"')
# => [['name', 'desc'], ['Alice', 'loves \"Python\"']]
""",
    ),
    (
        "Write a Python function that retries an async coroutine with exponential backoff.",
        "Python",
        """\
import asyncio
import functools
from typing import Callable, Type, Tuple

def async_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    def decorator(coro_fn: Callable):
        @functools.wraps(coro_fn)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return await coro_fn(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise
                    await asyncio.sleep(delay)
                    delay *= backoff
        return wrapper
    return decorator
""",
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# CONVERTERS
# ─────────────────────────────────────────────────────────────────────────────

def _sha8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:8]


class GeneralCodingConverter:
    """Yields JSONL entries from the built-in general coding corpus."""

    def convert(self) -> Generator[Dict, None, None]:
        for instruction, language, solution in _BUILTIN_TASKS:
            user_content = f"Language: {language}\n\n{instruction}"
            group_key = f"general_{_sha8(instruction)}"
            yield {
                "messages": [
                    {"role": "system",    "content": GENERAL_SYSTEM_PROMPT},
                    {"role": "user",      "content": user_content},
                    {"role": "assistant", "content": solution.strip()},
                ],
                "_meta": {
                    "source":    "general_coding",
                    "cve_id":    None,
                    "cwe_id":    None,
                    "group_key": group_key,
                },
            }


class CodeAlpacaConverter:
    """
    Downloads sahil2801/CodeAlpaca-20k from HuggingFace.
    Requires:  pip install datasets
    Falls back to GeneralCodingConverter if unavailable.
    """
    HF_DATASET = "sahil2801/CodeAlpaca-20k"

    def convert(self, max_samples: int = 2000) -> Generator[Dict, None, None]:
        try:
            from datasets import load_dataset  # type: ignore
        except ImportError:
            logger.warning(
                "HuggingFace `datasets` not installed. "
                "Falling back to built-in corpus. "
                "Install with: pip install datasets"
            )
            yield from GeneralCodingConverter().convert()
            return

        logger.info(f"Downloading {self.HF_DATASET} …")
        try:
            ds = load_dataset(self.HF_DATASET, split="train",
                              streaming=False, trust_remote_code=False)
        except Exception as e:
            logger.error(f"Failed to load CodeAlpaca: {e}. Falling back to built-in.")
            yield from GeneralCodingConverter().convert()
            return

        count = 0
        for row in ds:
            if count >= max_samples:
                break
            instruction = (row.get("instruction") or "").strip()
            output      = (row.get("output") or "").strip()
            if not instruction or not output:
                continue
            # CodeAlpaca has an optional 'input' field
            inp = (row.get("input") or "").strip()
            user_content = instruction + (f"\n\nInput:\n{inp}" if inp else "")
            group_key = f"codealp_{_sha8(instruction)}"
            yield {
                "messages": [
                    {"role": "system",    "content": GENERAL_SYSTEM_PROMPT},
                    {"role": "user",      "content": user_content},
                    {"role": "assistant", "content": output},
                ],
                "_meta": {
                    "source":    "codealp",
                    "cve_id":    None,
                    "cwe_id":    None,
                    "group_key": group_key,
                },
            }
            count += 1

        logger.info(f"CodeAlpaca: loaded {count} entries")


# ─────────────────────────────────────────────────────────────────────────────
# MIX-IN LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def load_existing_train(train_file: Path):
    """Load existing train.jsonl, return (entries, seen_content_hashes)."""
    entries, seen = [], set()
    if not train_file.exists():
        return entries, seen
    with train_file.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                content = entry["messages"][1]["content"]
                seen.add(_sha8(content))
                entries.append(entry)
            except Exception:
                pass
    return entries, seen


def mix_general_data(
    train_file: Path,
    general_entries: List[Dict],
    ratio: float,
    seed: int = 42,
    dry_run: bool = False,
) -> Dict:
    """
    Inject `ceil(n_train * ratio)` general coding entries into train.jsonl.
    Returns a stats dict.
    """
    existing, seen_hashes = load_existing_train(train_file)
    n_existing = len(existing)
    n_inject   = math.ceil(n_existing * ratio)

    logger.info(f"Existing train entries : {n_existing:,}")
    logger.info(f"Target injection count : {n_inject:,}  ({ratio*100:.0f}% of {n_existing:,})")

    # Deduplicate general entries against existing content
    rng = random.Random(seed)
    new_candidates = [
        e for e in general_entries
        if _sha8(e["messages"][1]["content"]) not in seen_hashes
    ]
    rng.shuffle(new_candidates)

    to_inject = new_candidates[:n_inject]
    skipped   = n_inject - len(to_inject)

    if skipped:
        logger.warning(
            f"{skipped} slots couldn't be filled "
            f"(corpus has {len(general_entries)} unique entries, "
            f"{len(new_candidates)} after dedup)"
        )

    logger.info(f"Injecting {len(to_inject):,} general coding entries …")

    if dry_run:
        logger.info("[DRY-RUN] No files written.")
        return {
            "n_security": n_existing,
            "n_general":  len(to_inject),
            "n_total":    n_existing + len(to_inject),
            "ratio_actual": len(to_inject) / (n_existing + len(to_inject)) if n_existing else 0,
            "dry_run": True,
        }

    # Strip _meta, shuffle, write back
    combined = existing + to_inject
    rng.shuffle(combined)

    with train_file.open("w", encoding="utf-8") as f:
        for entry in combined:
            clean = {k: v for k, v in entry.items() if k != "_meta"}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")

    n_total = len(combined)
    actual_ratio = len(to_inject) / n_total if n_total else 0
    logger.info(
        f"✅  train.jsonl: {n_existing:,} security + {len(to_inject):,} general "
        f"= {n_total:,} total  ({actual_ratio*100:.1f}% general)"
    )
    return {
        "n_security": n_existing,
        "n_general":  len(to_inject),
        "n_total":    n_total,
        "ratio_actual": actual_ratio,
        "dry_run": False,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ouroboros – General Coding Data Injector (Task 2.2)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--train-file", type=Path, default=Path("data/splits/train.jsonl"),
        help="Path to training split JSONL (default: data/splits/train.jsonl)",
    )
    parser.add_argument(
        "--ratio", type=float, default=0.08,
        help="Fraction of general coding examples to inject (default: 0.08 = 8%%)",
    )
    parser.add_argument(
        "--source", choices=["builtin", "codealp"], default="builtin",
        help="General coding data source: 'builtin' (default) or 'codealp' (HF CodeAlpaca)",
    )
    parser.add_argument("--seed",   type=int, default=42)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be injected without modifying any files",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not 0 < args.ratio < 1:
        logger.error("--ratio must be between 0 and 1 (e.g. 0.08 for 8%%)")
        sys.exit(1)

    logger.info("═" * 62)
    logger.info("Ouroboros — General Coding Data Injector  (Task 2.2)")
    logger.info("═" * 62)
    logger.info(f"Train file : {args.train_file.resolve()}")
    logger.info(f"Source     : {args.source}")
    logger.info(f"Ratio      : {args.ratio*100:.0f}%")
    logger.info(f"Dry-run    : {args.dry_run}")

    # Generate general coding entries
    if args.source == "codealp":
        converter = CodeAlpacaConverter()
        general_entries = list(converter.convert())
    else:
        converter = GeneralCodingConverter()
        general_entries = list(converter.convert())

    logger.info(f"General corpus size: {len(general_entries):,} entries")

    # Mix in
    stats = mix_general_data(
        train_file=args.train_file,
        general_entries=general_entries,
        ratio=args.ratio,
        seed=args.seed,
        dry_run=args.dry_run,
    )

    # Report
    print("\n" + "═" * 52)
    print(f"  {'Metric':<28} {'Value':>12}")
    print("─" * 52)
    print(f"  {'Security entries':<28} {stats['n_security']:>12,}")
    print(f"  {'General coding entries':<28} {stats['n_general']:>12,}")
    print(f"  {'Total entries':<28} {stats['n_total']:>12,}")
    print(f"  {'Actual general ratio':<28} {stats['ratio_actual']*100:>11.1f}%")
    print(f"  {'Dry-run':<28} {str(stats['dry_run']):>12}")
    print("═" * 52 + "\n")


if __name__ == "__main__":
    main()
