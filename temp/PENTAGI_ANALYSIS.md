# PentAGI - Comprehensive Analysis Report

## 📋 Overview

**PentAGI** stands for **Penetration Testing Artificial General Intelligence** - an innovative, autonomous security testing platform that leverages cutting-edge AI technologies for automated penetration testing and vulnerability assessment.

---

## 🔬 20+ Pentesting Tools - Complete List

PentAGI includes a comprehensive suite of professional security tools, organized by category:

### 1. **Network Reconnaissance & Scanning** (21 tools)
Used for initial target discovery, port scanning, service enumeration, subdomain hunting, DNS reconnaissance:
- `nmap` - Port scanning, OS fingerprinting, service detection
- `masscan` - High-speed port scanner
- `nping` - Network packet generation and response analysis
- `amass` - Network mapping and DNS enumeration
- `theharvester` - Email and subdomain gathering
- `subfinder` - Subdomain discovery
- `shuffledns` - DNS subdomain brute-forcing
- `dnsx` - DNS query tool with multiple options
- `assetfinder` - Find subdomains owned by given domain
- `chaos` - Passive subdomain discovery
- `dnsrecon` - DNS reconnaissance
- `fierce` - DNS reconnaissance
- `netdiscover` - Network discovery via ARP spoofing
- `arp-scan` - ARP-based network mapping
- `arping` - ARP request ping
- `fping` - Fast ping utility
- `hping3` - TCP/IP packet generator
- `nbtscan` - NetBIOS network scanner
- `onesixtyone` - SNMP service scanner
- `sublist3r` - Subdomain enumeration
- `ncrack` - High-speed network authentication cracking
- `ike-scan` - IKE (IPsec) protocol scanner

### 2. **Web Application Testing** (20 tools)
Web application security assessment, directory brute-forcing, vulnerability scanning, content discovery:
- `gobuster` - Directory and DNS brute-forcing
- `dirb` - Directory brute-forcing
- `dirsearch` - Directory brute-forcing with advanced options
- `feroxbuster` - Fast directory brute-forcing
- `ffuf` - Fuzzing and content discovery
- `nikto` - Web server vulnerability scanner
- `whatweb` - Web technology identification
- `sqlmap` - SQL injection detection and exploitation
- `wfuzz` - HTTP parameter fuzzing
- `wpscan` - WordPress vulnerability scanner
- `commix` - Command injection testing
- `davtest` - WebDAV exploitation
- `skipfish` - Active web application scanner
- `httpx` - HTTP probe and parameter detection
- `katana` - Web crawler and parameter discovery
- `hakrawler` - Web crawler for security
- `waybackurls` - Historical URL retrieval
- `gau` - Fetch known URLs from AlienVault OTX
- `nuclei` - Template-based vulnerability scanner
- `naabu` - Port discovery and scanning

### 3. **Password & Credential Attacks** (8 tools)
Credential attacks, hash cracking, brute-force authentication, password list generation:
- `hydra` - Network service brute-force
- `john` - Password hash cracking (The John the Ripper)
- `hashcat` - GPU-accelerated hash cracking
- `crunch` - Dictionary/wordlist generator
- `medusa` - Parallel password cracking tool
- `patator` - Multi-protocol password cracking
- `hashid` - Hash type identifier
- `hash-identifier` - Hash type identification
- Plus: `*2john` utilities for converting various formats (7z, bitcoin, keepass, office, pdf, rar, ssh, zip, gpg, putty, truecrypt, luks)

### 4. **Metasploit Framework** (9 tools)
Exploitation framework for developing and executing exploits, payload generation, pattern analysis:
- `msfconsole` - Main Metasploit console
- `msfvenom` - Payload generator
- `msfdb` - Metasploit database management
- `msfrpc` - Metasploit RPC interface
- `msfupdate` - Update Metasploit
- `msf-pattern_*` - Pattern generation for exploit development
- `msf-find_badchars` - Find bad characters for shellcode
- `msf-egghunter` - Egg hunter generation
- `msf-makeiplist` - IP list generation

### 5. **Windows & Active Directory** (16 tools)
Windows and Active Directory exploitation, lateral movement, credential extraction, Kerberos attacks:
- `impacket-*` - Suite of impacket tools (ntlmrelayx, psexec, wmiexec, etc.)
- `evil-winrm` - Windows Remote Management exploitation
- `bloodhound-python` - Active Directory mapping and analysis
- `crackmapexec` - Network authentication and lateral movement
- `netexec` - Active Directory exploration and exploitation
- `responder` - LLMNR/NBT-NS spoofing and credential capture
- `certipy-ad` - Active Directory certificate exploitation
- `ldapdomaindump` - LDAP domain enumeration
- `enum4linux` - Windows/Samba enumeration
- `smbclient` - SMB client utilities
- `smbmap` - SMB share enumeration and mapping
- `mimikatz` - Windows credential harvesting
- `lsassy` - LSASS process credential extraction
- `pypykatz` - Python implementation of Mimikatz
- `pywerview` - Python rewrite of PowerView
- `minikerberos-*` - Kerberos tools

### 6. **Post-Exploitation & Persistence** (11 tools)
Persistence, pivoting, tunneling, maintaining access, command and control frameworks:
- `powershell-empire` - PowerShell post-exploitation framework
- `starkiller` - Empire GUI
- `unicorn-magic` - PowerShell shellcode injection
- `weevely` - PHP web shell
- `proxychains4` - Proxy chaining for tunneling
- `chisel` - Fast TCP tunneling
- `iodine` - DNS tunneling
- `ptunnel` - ICMP tunneling
- `socat` - Network/data relay
- `netcat` - Network utility (nc, ncat) - Classic Swiss army knife
- `ncat` - Netcat alternative

### 7. **Traffic Analysis & MITM** (9 tools)
Network traffic interception, protocol analysis, SSL/TLS testing, man-in-the-middle attacks:
- `tshark` - Terminal-based packet analyzer (Wireshark CLI)
- `tcpdump` - Network packet capture
- `tcpreplay` - Packet replay utility
- `mitmdump` - MITM proxy (command-line)
- `mitmproxy` - MITM proxy (interactive)
- `mitmweb` - MITM proxy (web interface)
- `sslscan` - SSL/TLS cipher suite scanning
- `sslsplit` - SSL/TLS traffic interception
- `stunnel4` - SSL/TLS tunneling

### 8. **Reverse Engineering & Binary Analysis** (16 tools)
Binary analysis, malware examination, firmware extraction, exploit development, steganography:
- `radare2` - Reverse engineering framework
- `r2` - Radare2 alias
- `rabin2` - ELF/PE binary analyzer
- `radiff2` - Binary diffing
- `binwalk` - Firmware analysis and extraction
- `bulk_extractor` - Bulk extraction from files
- `ROPgadget` - ROP gadget finder
- `ropper` - ROP gadget search tool
- `strings` - String extraction from binaries
- `objdump` - Object file disassembler
- `steghide` - Steganography tool
- `foremost` - Forensic recovery tool

### 9. **OSINT & Intelligence Gathering** (5+ resources)
Intelligence gathering, exploit database searches, public data collection, wordlist resources:
- `searchsploit` - Exploit database search (Exploit-DB)
- `shodan` - Internet-connected devices database access
- `censys` - Certificate and website search engine access
- `/usr/share/wordlists` - Common wordlist directory
- `/usr/share/seclists` - SecLists wordlist collection

---

## 🧠 Memory & RAG System - Graph-Based Approach

### Memory Architecture

PentAGI implements a sophisticated multi-layered memory system designed for long-term learning and context retention:

#### **1. Long-term Memory (Persistent Storage)**

**Vector Store (PostgreSQL + pgvector)**
- Stores embeddings of all research results and findings
- Enables semantic similarity search for retrieving relevant past experiences
- Uses pgvector extension for vector operations
- Persists all action outcomes and successful approaches

**Knowledge Base (Domain Expertise)**
- Structured repository of security testing methodologies
- Stores tool capabilities and usage patterns
- Contains vulnerability information and exploitation techniques
- Provides context for decision-making

**Tools Knowledge**
- Stores successful tool usage patterns
- Maintains command syntax and parameters for each tool
- Tracks tool-specific limitations and workarounds
- Records tool version compatibility notes

#### **2. Working Memory (Active Context)**

**Current Context**
- Active task state and progress
- Current target information
- Recent findings and observations
- Active goals and objectives

**Active Goals**
- Current penetration testing objectives
- Attack path targets
- Success criteria for current operations
- Priority tasks

**System State**
- Available resources (ports, containers, memory)
- Tool availability status
- Network configuration
- Container capabilities

#### **3. Episodic Memory (Historical Records)**

**Past Actions**
- Complete command history executed
- All tool invocations and parameters
- File operations and modifications
- Failed attempts and recovery strategies

**Action Results**
- Output from each command execution
- Success/failure status
- Artifacts produced (reports, files, evidence)
- Error messages and diagnostics

**Success Patterns**
- Best practices discovered during testing
- Successful exploitation techniques
- Effective reconnaissance methods
- Proven attack sequences

### RAG (Retrieval-Augmented Generation) Integration

PentAGI uses a sophisticated RAG approach enhanced with graph databases:

#### **Graph-Based Knowledge Representation**

**Neo4j Graph Database**
- Stores semantic relationships between entities
- Connected nodes represent:
  - **Vulnerabilities** ↔ **Tools** (which tool can exploit which vulnerability)
  - **Services** ↔ **Exploits** (services vulnerable to specific exploits)
  - **Hosts** ↔ **Discovered Information** (reconnaissance results)
  - **Attack Paths** (chains of vulnerabilities leading to objectives)

**Graphiti Integration**
- Knowledge graph API for semantic relationship tracking
- Provides advanced context understanding beyond keyword matching
- Enables relationship-based queries:
  - "Find all vulnerabilities related to this service"
  - "What exploitation chains lead to privilege escalation?"
  - "Which tools are effective against this vulnerability type?"

#### **Query Flow**

```
1. Incoming Task/Query
   ↓
2. Vector Store Search (Semantic Similarity)
   - Finds similar past experiences
   - Retrieves relevant findings
   ↓
3. Graph Database Query (Relationship Analysis)
   - Follows relationship chains
   - Identifies connected entities
   - Discovers exploitation paths
   ↓
4. Context Synthesis
   - Combines vector search + graph results
   - Creates comprehensive context
   ↓
5. LLM Processing
   - Agent receives augmented context
   - Makes informed decisions
   - Generates next actions
```

#### **Memory Search Types**

1. **Recent Context Search**
   - Retrieves latest relevant findings
   - Time-window based filtering
   - Example: "recent nmap scan results for 192.168.1.100"

2. **Successful Tools Search**
   - Finds proven techniques and commands
   - Filters by success metrics
   - Example: "successful sqlmap commands against MySQL"

3. **Episode Context Search**
   - Retrieves complete agent reasoning and analysis
   - Includes decision-making context
   - Example: "pentester agent analysis of SSH vulnerability"

4. **Entity Relationship Search**
   - Explores connections between discovered entities
   - Follows graph relationships
   - Example: "What services/vulnerabilities are related to this entity?"

### Context Management & Chain Summarization

**Token-Aware Summarization**
- Prevents LLM context window overflow
- Preserves critical conversation flow
- Selectively summarizes older messages while keeping recent ones
- Implements QA (Question-Answer) pair summarization for efficiency

**Configuration:**
- `SUMMARIZER_PRESERVE_LAST=true` - Keep recent messages intact
- `SUMMARIZER_USE_QA=true` - Use QA pair strategy
- `SUMMARIZER_LAST_SEC_BYTES=51200` - 50KB for last section (not summarized)
- `SUMMARIZER_MAX_QA_SECTIONS=10` - Maximum QA sections to preserve

---

## 📊 Monitoring Tools & Advantages

### **1. Observability Stack**

#### **OpenTelemetry (OTEL)**
- **Purpose:** Unified data collection from all PentAGI components
- **Function:** Correlates metrics, traces, and logs across the system
- **Advantage:** Single standard for observability (vendor-neutral)

#### **Grafana**
- **Purpose:** Real-time visualization and alerting dashboards
- **Data Sources:**
  - VictoriaMetrics (metrics)
  - Jaeger (traces)
  - Loki (logs)
- **Advantages:**
  - Visual representation of system health
  - Real-time alert configuration
  - Custom dashboard creation
  - Pre-built Kubernetes dashboards

#### **VictoriaMetrics**
- **Purpose:** High-performance time-series database
- **Stores:** System metrics, resource usage, performance data
- **Advantages:**
  - 10x better compression than Prometheus
  - Lower memory footprint
  - Better query performance at scale
  - Real-time data ingestion

#### **Jaeger**
- **Purpose:** Distributed tracing across microservices
- **Tracks:**
  - API request flows
  - Database queries
  - Service-to-service calls
  - Tool execution timings
- **Advantages:**
  - Identify performance bottlenecks
  - Trace request failures end-to-end
  - Visualize system dependencies
  - Debug latency issues

#### **Loki**
- **Purpose:** Scalable log aggregation
- **Features:**
  - Multi-label based indexing
  - Efficient storage (100x less disk)
  - Fast log querying
  - Integration with Grafana
- **Advantages:**
  - Cost-effective log storage
  - Easy label-based searching
  - No need for pre-defined schema
  - Horizontal scalability

### **2. LLM Analytics & Monitoring**

#### **Langfuse**
- **Purpose:** Comprehensive LLM observability and performance analytics
- **Monitors:**
  - LLM API calls and responses
  - Token usage and costs
  - Latency and performance
  - Model behavior and output quality
- **Storage:**
  - ClickHouse (analytics data warehouse)
  - Redis (caching layer)
  - MinIO (file storage)
- **Advantages:**
  - Track LLM performance over time
  - Cost optimization and budgeting
  - Identify model improvement opportunities
  - Compliance and audit trails

### **3. Analytics Infrastructure**

#### **ClickHouse**
- **Purpose:** Column-oriented analytics data warehouse
- **Stores:** All analytics events, metrics, and performance data
- **Advantages:**
  - OLAP optimized (analytical queries)
  - 100-1000x faster query speeds than traditional databases
  - Excellent compression ratios
  - Real-time data ingestion

#### **Redis**
- **Purpose:** Caching layer and rate limiting
- **Functions:**
  - Cache frequently accessed data
  - Rate limit API requests
  - Session management
  - Real-time counters
- **Advantages:**
  - Sub-millisecond response times
  - Reduce database load
  - API throttling and protection
  - High throughput (100k+ ops/sec)

#### **MinIO**
- **Purpose:** S3-compatible object storage for artifacts
- **Stores:**
  - Reports and findings
  - Tool outputs and logs
  - Scan results and evidence
  - Media and documentation
- **Advantages:**
  - S3-compatible API (no vendor lock-in)
  - High availability and replication
  - Encryption at rest and in transit
  - Cost-effective storage

---

## 📈 System Monitoring Advantages Summary

| Component | Key Advantage |
|-----------|---------------|
| **OpenTelemetry** | Unified observability standard, vendor-agnostic |
| **Grafana** | Visual dashboards with real-time alerts |
| **VictoriaMetrics** | 10x better compression, lower resource usage |
| **Jaeger** | End-to-end distributed tracing, bottleneck identification |
| **Loki** | Cost-effective log storage (100x less disk) |
| **Langfuse** | Complete LLM performance and cost tracking |
| **ClickHouse** | 1000x faster analytics queries, real-time insights |
| **Redis** | Sub-millisecond caching, rate limiting |
| **MinIO** | S3-compatible object storage, data durability |

---

## 🎯 Multi-Agent Architecture

PentAGI employs specialized AI agents working in coordination:

1. **Orchestrator** - Coordinates overall flow
2. **Researcher (Searcher Agent)** - Gathers intelligence and reconnaissance *(see detailed breakdown below)*
3. **Developer** - Develops custom exploits and payloads
4. **Executor** - Performs hands-on penetration testing
5. **Adviser** - Strategic decision-making
6. **Enricher** - Context enrichment specialist *(see detailed breakdown below)*
7. **Memorist** - Manages learning and knowledge retrieval
8. **Installer** - Environment setup and tool configuration

Each agent accesses the shared memory systems (Vector Store + Graph DB) and contributes to the knowledge base.

---

## 🔍 Research Agent (Searcher) — Deep Dive

### Overview

The Researcher/Searcher agent is officially titled **"PRECISION INFORMATION RETRIEVAL SPECIALIST"** — an elite search intelligence agent optimized for maximum efficiency. Its core mission is to deliver the most relevant information with the **fewest possible actions**.

It is invoked whenever the Primary Agent (Orchestrator) or other agents need external intelligence, vulnerability research, exploit techniques, OSINT data, or technical documentation.

### Core Design Principles

| Principle | Description |
|-----------|-------------|
| **Action Economy** | Hard cap of **3–5 search actions maximum** per query. Stop immediately once enough info is gathered. |
| **Memory-First** | **Always** check the internal Vector DB (`search_answer`) before hitting any external search API |
| **Source Prioritization** | Internal memory → Specialized tools → General search engines |
| **No Redundancy** | Never repeat searches with similar queries; decompose complex questions into distinct searchable components |
| **Precision Queries** | Use exact technical terms, CVE identifiers, error codes, and specific tool names |

### Search Tool Deployment Matrix (Priority Order)

The Searcher agent has access to up to **11 tools**, conditionally registered based on available API keys/configs:

| Priority | Tool | Category | Purpose | Condition |
|----------|------|----------|---------|-----------|
| 🥇 1 | `search_answer` | Memory (Vector DB) | **PRIMARY** — Check existing knowledge via semantic similarity search | pgvector Store configured |
| 🥇 1 | `store_answer` | Memory (Vector DB) | Store newly discovered valuable information for future use | pgvector Store configured |
| 🥈 2 | `memorist` | Memory (Delegation) | Retrieve task/subtask execution history and context from Memorist agent | Always available |
| 🥉 3 | `google` | Reconnaissance | Fast query, shortest content — check information or collect public links | `GOOGLE_API_KEY` configured |
| 🥉 3 | `duckduckgo` | Reconnaissance | Anonymous query — returns small content from different sources, privacy-sensitive | `DUCKDUCKGO_ENABLED=true` |
| 4 | `browser` | Deep Extraction | Opens an isolated browser to extract targeted content from specific URLs | `SCRAPER_PRIVATE_URL` configured |
| 4 | `traversaal` | Deep Analysis | Presents answers and web-links by query according to relevant information | `TRAVERSAAL_API_KEY` configured |
| 5 | `tavily` | Deep Analysis | More complex query — detailed content with answers and info from websites | `TAVILY_API_KEY` configured |
| 5 | `perplexity` | Deep Analysis | Fully complex query — detailed research report augmented by LLM reasoning | `PERPLEXITY_API_KEY` configured |
| 5 | `searxng` | Meta Search | Privacy-focused meta search engine aggregating results from multiple engines | `SEARXNG_URL` configured |

### How It Works — Search Flow

```
Incoming Query (from Primary Agent or Pentester)
    │
    ▼
┌─────────────────────────────────────────┐
│  Step 1: search_answer (Vector DB)      │ ◄── ALWAYS first
│  Check if we already know the answer    │
│  Similarity threshold: 0.2, limit: 3   │
└───────────────┬─────────────────────────┘
                │
        Found enough? ──YES──► Deliver via search_result ✅
                │
               NO
                │
                ▼
┌─────────────────────────────────────────┐
│  Step 2: memorist (Delegation)          │
│  Check task execution history/context   │
└───────────────┬─────────────────────────┘
                │
        Found enough? ──YES──► Deliver via search_result ✅
                │
               NO
                │
                ▼
┌─────────────────────────────────────────┐
│  Step 3: External Search Tools          │
│  google / duckduckgo (reconnaissance)   │
│  browser / traversaal (deep extraction) │
│  tavily / perplexity / searxng (deep)   │
│  MAX 3-5 total actions                  │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Step 4: store_answer (if new info)     │
│  Persist valuable findings to Vector DB │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Step 5: search_result (Barrier Tool)   │
│  Deliver comprehensive answer + message │
│  Terminates the searcher agent loop     │
└─────────────────────────────────────────┘
```

### Vector DB Integration

The Searcher agent directly integrates with PostgreSQL + pgvector for persistent knowledge:

**`search_answer` (Retrieval)**
- Performs **semantic similarity search** with threshold **0.2** and returns top **3 documents**
- Filters by `doc_type: "answer"` and specific `answer_type` (guide / vulnerability / code / tool / other)
- Returns documents with relevance score, original question, answer type, and content
- Full audit trail logged to VectorStoreLogProvider
- Observable via Langfuse (retriever spans with scores)

**`store_answer` (Storage)**
- Stores answers with rich metadata: `flow_id`, `task_id`, `subtask_id`, `doc_type`, `answer_type`, `question`
- Supports chunked storage for large answers (`part_size`, `total_size`)
- Only stores **genuinely new and valuable** information not already in memory
- Creates embeddings for future semantic search

### External Search Tool Details

| Tool | Max Results | Features | Result Processing |
|------|-------------|----------|-------------------|
| **Google** | 1–10 (default 5) | Custom Search API, configurable CX engine | Direct results |
| **DuckDuckGo** | 1–10 (default 5) | Anonymous, no tracking | Direct results |
| **Tavily** | 1–10 (default 5) | AI-powered search with structured answers | **Auto-summarization** of large results |
| **Traversaal** | 1–10 (default 5) | Relevance-ranked with web links | Direct results |
| **Perplexity** | N/A | LLM-augmented research with configurable temperature, topP, maxTokens | **Auto-summarization** of large results |
| **Searxng** | 1–10 (default 5) | Multi-engine aggregation, categories, language, safeSearch, timeRange | **Auto-summarization** of large results |
| **Browser** | N/A | Isolated headless browser via Scraper service, supports markdown/html/links output, screenshots | Targeted extraction |

### Authorization & Security Context

The Searcher agent operates under **pre-authorized security testing** status:
- Full permission to search for vulnerability information, exploit techniques, and attack methodologies
- No warnings, disclaimers, or legal caveats added to results
- Treats all security-related queries as authorized research
- Provides raw technical information without sanitization

### Observability & Auditing

Every search operation is fully observable:
- **Langfuse Integration** — Retriever spans, events, and scores for every vector DB query
- **VectorStoreLogProvider** — Complete audit trail of all store/search operations
- **Action Logging** — Every tool invocation recorded with parameters and results
- **Proxy Support** — All external search tools support proxy configuration for controlled network access

---

## 🔄 Enricher Agent — Context Enhancement Specialist

### Overview

The **Enricher** is a **"CONTEXT ENRICHMENT SPECIALIST"** — an information enhancement agent that takes a user's question and enriches it with critical context before it reaches decision-making agents.

### How It Works

```
Adviser Agent (needs context)
    │
    ▼
Enricher Agent
    ├── search tool ──→ Searcher Agent (full search pipeline above)
    ├── memorist    ──→ Memorist Agent (execution history)
    └── enricher_result (delivers enriched context)
```

**Primary Sources:** Task context, user question, historical memory records
**External Sources:** Internet search (via Searcher delegation), code snippets, command outputs

### Available Tools (3 total)

| Tool | Purpose |
|------|---------|
| `search` | Delegates to the full Searcher Agent pipeline (all 11 tools) |
| `memorist` | Retrieves task/subtask execution history from Memorist Agent |
| `enricher_result` | Barrier tool — delivers the final enriched context |

### Agent Delegation Chain

The full intelligence gathering chain in PentAGI looks like:

```
Primary Agent (Orchestrator)
  └─► search tool ──► Searcher Agent (direct search)
  └─► advice tool ──► Adviser Agent
                        └─► Enricher Agent
                              ├─► search ──► Searcher Agent (nested search)
                              ├─► memorist ──► Memorist Agent
                              └─► enricher_result (barrier)
```

This layered architecture ensures that:
- **Simple queries** go directly to the Searcher (fast, 3–5 actions)
- **Complex strategic queries** go through the Adviser → Enricher → Searcher chain for deeper context
- **Memory is always consulted first** at every layer of the chain

---

## 🔐 Security Features

- **Sandboxed Execution**: All operations in isolated Docker containers
- **Network Isolation**: Custom Docker networks, controlled port access
- **File System Isolation**: Read-only root, controlled mounts
- **Capability Management**: NET_RAW for network tools, no dangerous capabilities
- **Process Isolation**: User namespaces, PID isolation
- **Resource Limits**: Memory and CPU constraints
- **Automatic Cleanup**: Failed containers automatically removed

---

## 📊 Data Flow

```
Pentester/User (UI)
    ↓
Backend API (REST/GraphQL)
    ↓
Task Queue (Async Processing)
    ↓
AI Agents (Multi-Agent System)
    ├→ Vector Store (Embeddings + Memories)
    ├→ Neo4j Graph DB (Knowledge Graph)
    ├→ Pentesting Tools (Sandboxed Containers)
    ├→ Search APIs (Tavily, Perplexity, etc.)
    └→ Web Scraper (Isolated Browser)
    
    ↓ Monitoring & Analytics
    
Telemetry Collection (OTEL)
    ├→ Grafana (Visualization)
    ├→ VictoriaMetrics (Metrics)
    ├→ Jaeger (Tracing)
    ├→ Loki (Logs)
    └→ Langfuse (LLM Analytics)
```

---

## 🚀 Key Capabilities

✅ **20+ Professional Pentesting Tools** - Comprehensive security toolkit
✅ **Graph-Based Knowledge System** - Semantic relationship tracking with Neo4j + Graphiti
✅ **RAG-Enhanced AI** - Vector search + graph relationships for context
✅ **Multi-Agent Collaboration** - Specialized agents for different tasks
✅ **Persistent Learning** - Long-term memory with episodic recall
✅ **Real-time Monitoring** - Complete system observability
✅ **LLM Analytics** - Comprehensive AI performance tracking
✅ **Cost Optimization** - Efficient storage and caching layers
✅ **Scalable Architecture** - Microservices design with horizontal scaling
✅ **Self-Hosted Solution** - Full data control and privacy

---

**Repository:** https://github.com/vxcontrol/pentagi.git
**License:** Check repository for details
