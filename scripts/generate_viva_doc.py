"""Generate professional Microsoft Word (.docx) project walkthrough and viva presentation guide."""

from pathlib import Path
import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DOCX = REPO_ROOT / "docs" / "PROJECT_WALKTHROUGH_AND_VIVA_SCRIPT.docx"
SCREENSHOTS_DIR = REPO_ROOT / "docs" / "screenshots"


def set_cell_background(cell, fill_hex: str):
    """Set background color of a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tc_pr.append(shd)


def set_cell_margins(cell, top=140, bottom=140, left=180, right=180):
    """Set internal padding/margins of a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tc_pr.append(tc_mar)


def add_callout(doc, text: str, title: str = "🎤 EXACT SCRIPT TO SAY TO MA'AM", bg_hex: str = "FEF9C3", border_hex: str = "D97706"):
    """Add a highlighted callout box for scripts or important notes."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, bg_hex)
    set_cell_margins(cell, top=160, bottom=160, left=200, right=200)

    # Set left border thick
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="36" w:space="0" w:color="{border_hex}"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tc_pr.append(borders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    run_t = p.add_run(f"{title}\n")
    run_t.bold = True
    run_t.font.size = Pt(10.5)
    run_t.font.color.rgb = RGBColor(146, 64, 14)  # Warm dark amber

    run_b = p.add_run(text)
    run_b.font.size = Pt(10)
    run_b.font.italic = False
    run_b.font.color.rgb = RGBColor(30, 41, 59)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)


def build_document():
    doc = docx.Document()

    # Page Margins (0.75 in)
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(0.75)
        s.bottom_margin = Inches(0.75)
        s.left_margin = Inches(0.75)
        s.right_margin = Inches(0.75)

    # Base Styles
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(30, 41, 59)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(4)

    # -------------------------------------------------------------------------
    # Cover / Header Box
    # -------------------------------------------------------------------------
    title_tbl = doc.add_table(rows=1, cols=1)
    title_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = title_tbl.cell(0, 0)
    set_cell_background(c, "1E3A8A")  # Royal Navy
    set_cell_margins(c, top=260, bottom=260, left=240, right=240)

    p_title = c.paragraphs[0]
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p_title.add_run("🎓 Master Project Walkthrough & BDA Viva Script\n")
    r1.bold = True
    r1.font.size = Pt(20)
    r1.font.color.rgb = RGBColor(255, 255, 255)

    r2 = p_title.add_run("ML-Driven NoSQL Pattern Selection for Retrieval-Augmented Generation (RAG) Workloads\n")
    r2.bold = True
    r2.font.size = Pt(13)
    r2.font.color.rgb = RGBColor(224, 231, 255)

    r3 = p_title.add_run("Subject: Big Data Analytics (BDA) • Author: Hiten Bhurani • Duration: 15–20 Mins")
    r3.font.size = Pt(10)
    r3.font.color.rgb = RGBColor(199, 210, 254)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # -------------------------------------------------------------------------
    # Section 1: Executive Overview & Problem Statement
    # -------------------------------------------------------------------------
    h1 = doc.add_heading("1. Executive Overview & Problem Statement", level=1)
    h1.style.font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph(
        "Modern enterprise AI systems rely heavily on Retrieval-Augmented Generation (RAG) to ground large language models "
        "in private, domain-specific corpora. However, a production RAG application does not have a single uniform data shape—it has "
        "heterogeneous data requirements spanning conversation caching, raw document passages, knowledge-graph entity links, and dense vector embeddings."
    )
    doc.add_paragraph(
        "Historically, system architects choose database engines based on developer familiarity, vendor marketing, or arbitrary rules of thumb "
        "(e.g., using MongoDB or PostgreSQL for everything). This unoptimized selection introduces between 2x and 17x latency overhead (regret) "
        "and severely inflates compute and memory infrastructure costs."
    )
    doc.add_paragraph(
        "Our Research Solution: We developed an Explainable Two-Stage Pattern Selector that combines deterministic feasibility filtering "
        "with lightweight, explainable machine learning. We experimentally validated the system with 1,356 physical in-container benchmark runs "
        "across Redis, MongoDB, Apache Cassandra, Neo4j, and Qdrant."
    )

    # -------------------------------------------------------------------------
    # Section 2: Big Data Analytics (BDA) Syllabus Alignment
    # -------------------------------------------------------------------------
    h2 = doc.add_heading("2. Big Data Analytics (BDA) Alignment & Core Concepts", level=1)
    h2.style.font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph(
        "This project is fundamentally a Big Data Systems and Polyglot Persistence investigation. Machine learning is simply "
        "a lightweight decision-making tool. The core BDA syllabus concepts demonstrated in this project are:"
    )

    bda_items = [
        ("The 4 Core NoSQL Paradigms", "In-Memory Key-Value (Redis 7.4), Document Store (MongoDB 7.0), Wide-Column Distributed Store (Apache Cassandra 4.1), Property Graph (Neo4j 5.26), and Dense Vector Store (Qdrant)."),
        ("Polyglot Persistence", "The architectural principle that complex Big Data applications must deploy multiple specialized database engines rather than forcing one monolithic engine to handle incompatible access patterns."),
        ("Distributed Storage Engine Internals", "Benchmarking Cassandra's Log-Structured Merge Tree (LSM-tree), CommitLog, Memtables, and SSTables vs MongoDB's WiredTiger BSON document cache vs Redis's in-memory C hash structures."),
        ("Internal Distributed Diagnostics", "Executing Cassandra's native nodetool proxyhistograms to inspect coordinator-level read/write microsecond histograms."),
        ("Information Retrieval at Scale (BEIR)", "Benchmarking dense vector similarity search over a real corpus of 5,183 scientific abstracts and 300 biomedical test queries (BEIR SciFact), evaluating Recall@10, NDCG@10, and MRR."),
    ]
    for title, desc in bda_items:
        p = doc.add_paragraph(style="List Bullet")
        r_t = p.add_run(f"{title}: ")
        r_t.bold = True
        p.add_run(desc)

    # -------------------------------------------------------------------------
    # Section 3: The Engineering Journey & Hardware Isolation
    # -------------------------------------------------------------------------
    h3 = doc.add_heading("3. Implementation & Engineering Journey (Laptop Hardware)", level=1)
    h3.style.font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph(
        "To execute this heavy Big Data empirical evaluation on a standard Windows 11 laptop (Intel Core i5-12500H, 16 GB RAM, NVMe SSD), "
        "strict resource control and systems engineering were applied:"
    )

    p_eng1 = doc.add_paragraph(style="List Bullet")
    p_eng1.add_run("Sequential Container Isolation: ").bold = True
    p_eng1.add_run("To strictly respect the 3 GB WSL2 memory cap, only one database container was executed at a time. After its benchmark matrix concluded, the container was cleanly stopped before starting the next engine.")

    p_eng2 = doc.add_paragraph(style="List Bullet")
    p_eng2.add_run("The Windows WSL2 Loopback Discovery: ").bold = True
    p_eng2.add_run("Initial host benchmarks exhibited an anomalous 48 ms latency for Cassandra writes on payloads >= 4 KB. Internal nodetool proxyhistograms proved Cassandra's internal server latency was only 258 microseconds! The 47.7 ms discrepancy was identified as a Windows WSL2 hypervisor packet-segmentation and delayed-ACK buffer relay delay. We resolved this by building a dedicated in-container client (nosql-rag-client:1.0) running directly on the Docker bridge network, reducing 8 KB writes to 0.491 ms (a 98x speedup). Earlier host runs were quarantined as host_port_forward_pilot.")

    p_eng3 = doc.add_paragraph(style="List Bullet")
    p_eng3.add_run("Concurrency Scaling (c=4 Multiprocessing): ").bold = True
    p_eng3.add_run("Multi-threaded Python benchmarking suffered an 80.6% queueing overhead at c=4 due to CPython's Global Interpreter Lock (GIL). Switching to dedicated worker processes (multiprocessing.spawn) increased throughput by 4.25x (from 4,580 to 19,490 ops/sec).")

    # -------------------------------------------------------------------------
    # Section 4: Screen-by-Screen Walkthrough with Screenshots
    # -------------------------------------------------------------------------
    h4 = doc.add_heading("4. Step-by-Step Screen Walkthrough & Script (With Screenshots)", level=1)
    h4.style.font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph(
        "Before presenting, start the Streamlit application in PowerShell:\n"
        "uv run streamlit run src/nosql_rag/dashboard/app.py\n"
        "Open http://localhost:8501 in full screen. Below is your screen-by-screen guide:"
    )

    screens = [
        {
            "num": "1",
            "title": "Screen 1: Header, Project Overview & Sidebar Provenance",
            "img": "01_overview_and_recommender_input.png",
            "elements": [
                "Main Header: Project Title, Author (Hiten Bhurani), and one-paragraph research summary.",
                "Left Sidebar: Hardware environment (Windows 11, Intel i5-12500H, NVMe SSD, WSL2 3GB RAM cap, in-container client).",
                "Data Provenance Summary Cards: 2,269 total raw records, 1,356 genuine in-container benchmark runs, 900 quarantined pilot runs.",
            ],
            "script": (
                "\"Good morning Ma'am. My project is 'ML-Driven NoSQL Pattern Selection for RAG Workloads'. "
                "As seen on the sidebar, this is an empirical Big Data study. Rather than relying on theoretical assumptions or synthetic simulations, "
                "we conducted physical benchmarks across 5 major NoSQL database engines running in Docker containers on local NVMe hardware.\n"
                "We recorded 1,356 genuine, validated benchmark runs across Redis, MongoDB, Cassandra, and Neo4j, with 0 errors. "
                "To maintain strict scientific integrity, earlier host-measured runs that suffered from Windows port-forwarding delays "
                "were quarantined as pilot data and completely excluded from our machine learning pipeline.\""
            ),
            "bda": "Polyglot Persistence, Empirical Systems Auditing, Data Provenance Tagging."
        },
        {
            "num": "2",
            "title": "Screen 2: Tab 1 — Interactive Pattern Recommender (Live ML & Dynamic Latency)",
            "img": "02_recommender_results_and_charts.png",
            "elements": [
                "Top Blue Banner: Empirical finding: Redis dominates single-key CRUD; Stage 1 handles specialized vector/graph routing.",
                "Workload Sliders: Query Type, Average Payload Size (128B to 16KB), Read Ratio (0.05 to 1.0), Dataset Records, and Concurrency (c=1, 4).",
                "Recommendation Card: Metric card showing 'Redis' via Stage 2 ML Performance Selection.",
                "Candidate Eligibility List: Shows why Redis, Mongo, Cassandra, and Neo4j are feasible, while Qdrant is excluded from scalar CRUD.",
                "Live Empirical Latency Comparison Table & Bar Charts: Dynamically slices genuine runs matching the slider inputs, comparing Median P95 and P50 latencies and calculating the latency penalty vs winner.",
                "SHAP Feature Attribution: Shows which feature shifted the model's decision (data size, write ratio, payload bytes).",
            ],
            "script": (
                "\"Now Ma'am, let me demonstrate our two-stage selector live in Tab 1. "
                "Suppose an engineer has an operational session cache workload with a 1,024-byte payload, an 80% read ratio, and a concurrency of 4. "
                "When I click 'Generate Recommendation', the system executes our trained Random Forest pipeline. It recommends Redis. "
                "Look at this dynamic comparison table and chart below: it pulls the actual empirical measurements from our matrix. "
                "For this exact workload slice, Redis delivers 0.20 ms P95 latency. If the developer had blindly chosen MongoDB, they would suffer 0.73 ms P95 latency (+262% slower), "
                "and Cassandra incurs 1.53 ms (+657% slower). "
                "Furthermore, our SHAP attribution table shows that the model chose Redis based on memory-bound data size and write ratio characteristics.\""
            ),
            "bda": "Operational Workload Characterization, Feature Importance via SHAP Game Theory, In-Memory Caching vs Disk Engines."
        },
        {
            "num": "3",
            "title": "Screen 3: Tab 2 — Stage 1 Compatibility Matrix",
            "img": "03_compatibility_matrix.png",
            "elements": [
                "Structured Data-Model Feasibility Matrix: Maps Key-Value, Document JSON, Partitioned Writes, Multi-hop Graph Traversal, Dense Vector ANN, and RAG Retrieval across all 5 databases.",
                "Stage 1 Routing Column: Explains deterministic routing to Qdrant/Neo4j vs passing to Stage 2 ML for CRUD.",
            ],
            "script": (
                "\"Here in Tab 2 is our Stage 1 Compatibility Matrix, which embodies the BDA principle of Polyglot Persistence. "
                "In scientific benchmarking, you cannot force all databases into a single flat comparison. For example, comparing Qdrant on key-value CRUD "
                "or comparing Redis on 3-hop graph traversal is architecturally invalid. "
                "Stage 1 acts as a deterministic feasibility gatekeeper: if a workload requires dense vector search or passage retrieval, "
                "it is routed natively to Qdrant. If it requires graph traversal, it routes directly to Neo4j. Only general CRUD workloads pass to Stage 2 ML.\""
            ),
            "bda": "NoSQL Taxonomy, Data Model Boundaries, Polyglot Architecture Design."
        },
        {
            "num": "4",
            "title": "Screen 4: Tab 3 — CRUD Benchmark Explorer (Live Slices)",
            "img": "04_crud_benchmark_explorer.png",
            "elements": [
                "Top Metric Cards: 2,269 total raw records, 1,356 genuine runs, 0.00% error rate.",
                "Completeness Audit Table: 100% completion across all target runs (Redis: 450/450, MongoDB: 450/450, Cassandra: 228/228, Neo4j: 228/228).",
                "Provenance Breakdown Table: Demonstrates separation of genuine runs from quarantined pilot runs.",
                "Section 3 Interactive Slices: Live filters for Concurrency (c=1, c=4), Payload Size, and Read Ratio with dynamically updating P95 Latency and Throughput bar charts.",
            ],
            "script": (
                "\"Tab 3 provides full auditing of our empirical data. "
                "Notice our completeness audit: Redis and MongoDB completed 150 profiles x 3 repetitions = 450 runs each. "
                "Cassandra and Neo4j completed the 76-profile subset x 3 repetitions = 228 runs each. "
                "In Section 3, I can dynamically slice the benchmark. When I switch concurrency from c=1 to c=4, notice how the throughput chart jumps "
                "from ~70 ops/sec to over 300 ops/sec per worker, while Redis maintains sub-0.2 millisecond P95 latency across all payload sizes.\""
            ),
            "bda": "Concurrency Scaling, Throughput vs Latency Trade-offs, Systems Quality Auditing."
        },
        {
            "num": "5",
            "title": "Screen 5: Tab 4 — Models & SHAP Explainability",
            "img": "05_models_and_shap.png",
            "elements": [
                "Degeneracy Disclosure: Explains why 1.0000 Accuracy/Macro-F1 is degenerate due to single-class Redis test set (models match majority baseline).",
                "Analysis Selector: Independent views for Analysis A (2 Engines, 150 Profiles) and Analysis B (4 Engines, 76 Profiles).",
                "Evaluation Tables: Test accuracy (1.0000) and 5-fold Grouped CV Macro-F1 (0.8979 for Analysis A; 1.0000 for Analysis B).",
                "Visualizations: Held-Out Confusion Matrix and Global SHAP Summary Feature Importance Plots.",
            ],
            "script": (
                "\"In Tab 4, we evaluate our Machine Learning classifiers: Decision Tree, Random Forest, and Gradient Boosting. "
                "Notice an important scientific finding we uncovered: in pure single-key point CRUD under local networking, in-memory Redis dominates "
                "disk-backed engines in 149 out of 150 workloads. Because the test set contains only Redis, our 1.0000 accuracy is mathematically degenerate—the models match the majority-class baseline. "
                "Rather than faking or manipulating the data to force artificial diversity, our paper reports this as an authentic empirical finding: "
                "in single-key CRUD, Machine Learning has no multi-class variance to learn; the true architectural specialization occurs in Stage 1.\""
            ),
            "bda": "Leakage-Safe Grouped Cross-Validation, Class Imbalance in Big Data Systems, SHAP Game Theory."
        },
        {
            "num": "6",
            "title": "Screen 6: Tab 5 — Latency Regret Analysis",
            "img": "06_latency_regret.png",
            "elements": [
                "Mathematical Formula: Regret(W) = (Latency_selected - Latency_oracle) / Latency_oracle.",
                "Summary Table: Oracle (0.0%), ML Recommender (0.0%), Always-Redis (0.0%), Always-MongoDB (+206.8% / +264.4%), Always-Cassandra (+576.1%), Always-Neo4j (+1,770.7%).",
                "Dynamic Latency Overhead Bar Chart: Visualizes the exact multiple of latency delay for each alternative store.",
            ],
            "script": (
                "\"Tab 5 presents Latency Regret, which measures how much latency penalty an engineer suffers if they pick the wrong database compared to the Oracle best. "
                "As the chart illustrates, our ML recommender and Redis achieve 0.00% regret. "
                "If a development team chooses MongoDB as their default operational store, they incur an average of +206.8% latency overhead (over 3x slower). "
                "Choosing Cassandra adds +576% latency overhead (almost 7x slower), and Neo4j adds +1,770% latency overhead for scalar CRUD. "
                "This empirically proves the cost of poor database selection in Big Data pipelines.\""
            ),
            "bda": "Latency Regret Metric, Oracle Optimization, Cost-Benefit Analysis of Big Data Infrastructure."
        },
        {
            "num": "7",
            "title": "Screen 7: Tab 6 — Specialized Vector (Qdrant) & Graph (Neo4j) Evaluation",
            "img": "07_retrieval_and_graph.png",
            "elements": [
                "Section 1 BEIR SciFact RAG Retrieval: 5,183 abstracts, 300 test queries. Recall@10 = 0.7833, NDCG@10 = 0.6451, MRR = 0.6047, P50 = 15.32 ms.",
                "Section 2 Native Qdrant Dense Vector ANN: 2,000 vectors, Recall@10 = 1.0000 (100%), P50 = 15.07 ms.",
                "Section 3 Neo4j Graph Traversal: 200 nodes, 600 edges, 2-hop depth, Throughput = 270.4 ops/sec, P50 = 2.99 ms.",
            ],
            "script": (
                "\"Tab 6 demonstrates the specialized non-CRUD workloads that form the other pillars of RAG. "
                "Here, we evaluated Qdrant on the complete BEIR SciFact biomedical benchmark using MiniLM embeddings. Evaluating all 300 test queries, "
                "Qdrant achieved a strong Recall@10 of 0.7833 and NDCG@10 of 0.6451 with an average retrieval latency of 15.3 ms. "
                "For Neo4j, we benchmarked native 2-hop neighbor traversals using Cypher. Neo4j achieved 270.4 ops/sec with a P50 latency of 2.99 ms, "
                "demonstrating why graph databases are essential for knowledge-graph entity lookups where relational joins would create severe performance bottlenecks.\""
            ),
            "bda": "Vector Similarity Search (HNSW), Graph Traversal (Index-Free Adjacency), Information Retrieval Metrics (Recall, NDCG, MRR)."
        },
        {
            "num": "8",
            "title": "Screen 8: Tab 7 — Methodology, Network Findings & Limitations",
            "img": "08_methodology_and_findings.png",
            "elements": [
                "Windows WSL2 Relay Stall Discovery: 40 ms hypervisor delay, internal nodetool proxyhistograms proof (258 microseconds vs 48 ms), in-container fix (98x speedup).",
                "Concurrency Validity: 80.6% queueing overhead in Python threading; multiprocessing 4.25x speedup.",
                "Ground Truth Degeneracy: Academic disclosure of Redis dominance.",
                "Limitations: Single host, sequential container isolation, untuned 512M heaps, 200-node demo graph.",
            ],
            "script": (
                "\"Finally, Tab 7 documents our core systems engineering contributions and research limitations. "
                "The most significant engineering finding was identifying the Windows WSL2 loopback virtualization bottleneck: host-forwarded ports introduced a 40 ms TCP delayed-ACK stall on payloads over 4KB. "
                "By diagnosing this via Cassandra's internal proxyhistograms and migrating to a pinned in-container client, we achieved true bare-metal sub-millisecond latencies. "
                "We also proved that multi-threaded Python benchmarking bottlenecks on the GIL at c=4, whereas process-based multiprocessing unlocked a 4.25x throughput speedup. "
                "In summary, Ma'am, this project combines empirical Big Data benchmarking, systems performance debugging, and explainable machine learning into an end-to-end operational selector.\""
            ),
            "bda": "Virtualization Overhead, Hypervisor Socket Profiling, Process Concurrency, Hardware Limitations."
        },
    ]

    for scr in screens:
        doc.add_heading(scr["title"], level=2).style.font.color.rgb = RGBColor(13, 148, 136)

        # Embed Image
        img_path = SCREENSHOTS_DIR / scr["img"]
        if img_path.exists():
            doc.add_picture(str(img_path), width=Inches(6.2))
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r_cap = p_cap.add_run(f"Figure {scr['num']}: Dashboard Interface — {scr['title']}")
            r_cap.italic = True
            r_cap.font.size = Pt(9)
            r_cap.font.color.rgb = RGBColor(100, 116, 139)

        # What is on screen
        p_what = doc.add_paragraph()
        p_what.add_run("What is Visible on Screen:").bold = True
        for elem in scr["elements"]:
            p_e = doc.add_paragraph(style="List Bullet")
            p_e.add_run(elem)

        # Callout script
        add_callout(doc, scr["script"])

        # BDA Concept
        p_bda = doc.add_paragraph()
        p_bda.add_run("Key BDA Concept Illustrated: ").bold = True
        r_bda = p_bda.add_run(scr["bda"])
        r_bda.italic = True
        doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # -------------------------------------------------------------------------
    # Section 5: Top 15 Tough Viva Questions & Bulletproof Answers
    # -------------------------------------------------------------------------
    h5 = doc.add_heading("5. Top 15 Tough Viva Questions & Bulletproof Answers", level=1)
    h5.style.font.color.rgb = RGBColor(30, 58, 138)

    qa_list = [
        ("Q1: Why did you use NoSQL databases instead of traditional RDBMS like PostgreSQL or MySQL?",
         "Ma'am, RAG workloads are inherently polyglot and high-velocity. Session memory requires sub-millisecond key-value lookups which in-memory Redis handles significantly faster than relational disk tables. Document passages are unstructured nested JSON suited for MongoDB. Multi-hop knowledge graphs incur costly recursive SQL JOINs in RDBMS, whereas Neo4j uses Index-Free Adjacency to traverse pointers in constant time O(1). Finally, vector embeddings require specialized vector indexes like HNSW, which Qdrant provides natively."),

        ("Q2: Why is your ML model's Accuracy and Macro-F1 1.0000? Isn't that overfitting?",
         "No Ma'am, it is not overfitting; it is mathematically degenerate. In single-key CRUD workloads under local in-container networking, in-memory Redis is physically faster than disk-backed stores across 99.3% of configurations. Because the held-out test partition contains only Redis winners, the majority-class baseline is already 1.0000. Our models simply reproduce the majority baseline. We explicitly documented this as an authentic empirical finding rather than artificially tampering with data to create fake diversity."),

        ("Q3: What is Latency Regret and why use it instead of standard Classification Accuracy?",
         "Accuracy treats all mistakes equally: predicting Store B when Store A was fastest is counted as a failure, regardless of whether Store B was 0.01 ms slower or 50 ms slower. Latency Regret measures the real-world operational penalty: (Latency_selected - Latency_oracle) / Latency_oracle. It tells an enterprise architect how much extra latency overhead their choice introduces compared to the ideal engine."),

        ("Q4: How does Cassandra achieve fast writes, and why was it slower than Redis here?",
         "Cassandra uses an LSM-Tree (Log-Structured Merge Tree) architecture: writes append sequentially to an in-memory Memtable and a disk CommitLog without in-place updates. While this is extremely fast for distributed disks (~0.6 ms P50 in our benchmark), Redis operates entirely in RAM heap memory without disk flushes on the critical write path, enabling sub-0.1 ms latencies."),

        ("Q5: What is Index-Free Adjacency in Neo4j?",
         "In a relational database, finding a node's neighbors requires a JOIN table and B-Tree index lookups (O(log N)). In Neo4j's property graph engine, each node holds direct physical memory pointers to its adjacent relationships and neighbor nodes. Traversal is accomplished by following pointers in O(1) time, independent of the total size of the graph."),

        ("Q6: Why did you need a Two-Stage architecture instead of training one ML model across all 5 databases?",
         "Because comparing specialized vector search in Qdrant or multi-hop graph traversal in Neo4j against single-key CRUD in Redis creates a category error—it is an apples-to-oranges comparison. Stage 1 enforces data-model eligibility deterministically. Stage 2 only compares engines on common CRUD ground where they are truly functionally interchangeable."),

        ("Q7: What is Grouped Cross-Validation (base_workload_id) and why was it necessary?",
         "In our benchmark, each base workload was evaluated at two concurrencies: c=1 and c=4. If random K-Fold splitting was used, the c=1 version of a workload could be in the training set while the c=4 version was in the test set, causing data leakage. By grouping on base_workload_id, all variations of a base workload are strictly isolated in either train or test, guaranteeing honest generalization evaluation."),

        ("Q8: What was the Windows WSL2 loopback issue you discovered?",
         "When benchmarking from the Windows host against Docker forwarded ports (127.0.0.1:PORT), payloads >= 4 KB stalled at 48 ms. Using Cassandra's internal nodetool proxyhistograms, we proved Cassandra was processing writes in 258 microseconds. The remaining 47.7 ms was a Windows WSL2 hypervisor packet-segmentation and delayed-ACK relay artifact. We resolved it by running our benchmark client inside the Docker bridge network."),

        ("Q9: Why did multi-threaded Python benchmarking fail at c=4?",
         "Python's CPython runtime uses a Global Interpreter Lock (GIL). When 4 threads concurrently execute socket I/O and latency measurement loops, thread synchronization lock contention creates an 80.64% queueing delay. Switching to process-based multiprocessing (multiprocessing.spawn) allocated independent Python processes to separate CPU cores, increasing throughput by 4.25x (from 4,580 to 19,490 ops/sec)."),

        ("Q10: What is BEIR SciFact and what do Recall@10 and NDCG@10 mean?",
         "BEIR SciFact is a standardized benchmark created by the Allen Institute for AI for scientific claim verification over 5,183 research abstracts. Recall@10 = 0.7833 means that in 78.33% of queries, the relevant ground-truth evidence abstract was successfully retrieved within the top 10 results. NDCG@10 = 0.6451 measures ranking quality, penalizing relevant documents that appear lower down the top-10 list."),

        ("Q11: What are the limitations of your experimental setup?",
         "1. Single-node local environment: we did not model multi-datacenter WAN latency or network partitions. 2. Constrained JVM heaps (512 MB) to respect host RAM limits. 3. Single-key CRUD focus: multi-field range scans or complex aggregations would showcase Cassandra and MongoDB's query planners more effectively."),

        ("Q12: How does SHAP explainability work in your dashboard?",
         "SHAP (SHapley Additive exPlanations) is based on cooperative game theory. It computes the marginal contribution of each workload feature (payload size, read ratio, concurrency, data size) toward shifting the model's output probability from the base expected value to the predicted database class."),

        ("Q13: What consistency levels did you use in Cassandra?",
         "We utilized single-node Cassandra with LOCAL_ONE consistency and prepared statements, ensuring that consistency coordination was deterministic and comparable to single-instance MongoDB and Redis."),

        ("Q14: Why does MongoDB incur over 200% latency regret relative to Redis?",
         "MongoDB uses the WiredTiger engine which must serialize documents to BSON, update document indexes, manage page cache locks, and write to a journal. Redis stores key-value pairs directly in unfragmented C memory structures with an in-memory hash index, eliminating serialization and cache-miss overheads."),

        ("Q15: If Redis is always the winner in CRUD, why do we need other NoSQL databases?",
         "Redis is memory-bound: storing terabytes of historical RAG corpora in RAM is cost-prohibitive. Furthermore, Redis does not natively support multi-hop graph traversals (Neo4j), horizontal partitioned petabyte scale (Cassandra), rich polymorphic document querying (MongoDB), or native HNSW vector similarity search (Qdrant). This is why our Two-Stage Architecture is essential."),
    ]

    for q, a in qa_list:
        p_q = doc.add_paragraph()
        p_q.paragraph_format.space_before = Pt(6)
        r_q = p_q.add_run(q)
        r_q.bold = True
        r_q.font.color.rgb = RGBColor(30, 58, 138)

        p_a = doc.add_paragraph()
        r_lbl = p_a.add_run("Bulletproof Answer: ")
        r_lbl.bold = True
        r_lbl.font.color.rgb = RGBColor(13, 148, 136)
        p_a.add_run(a)

    # -------------------------------------------------------------------------
    # Section 6: Presentation Day Pro-Tips
    # -------------------------------------------------------------------------
    h6 = doc.add_heading("6. Presentation Day Pro-Tips & Checklist", level=1)
    h6.style.font.color.rgb = RGBColor(30, 58, 138)

    tips = [
        "Pre-Launch the Dashboard: Run 'uv run streamlit run src/nosql_rag/dashboard/app.py' and keep http://localhost:8501 full screen before Ma'am arrives.",
        "Interact with Sliders Live: Move the Payload slider to 8192 Bytes and click 'Generate Recommendation'. Seeing dynamic charts change live proves zero fabrication.",
        "Emphasize BDA Terminology: Frequently use terms like Polyglot Persistence, LSM-Trees, Index-Free Adjacency, HNSW Vector Indexing, WiredTiger, and nodetool proxyhistograms.",
        "Be Proud of the 1.0000 ML Score: Confidently explain that it reflects Redis's physical RAM dominance in single-key CRUD, not artificial overfitting.",
    ]
    for t in tips:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(t)

    doc.save(str(OUTPUT_DOCX))
    print(f"Successfully generated: {OUTPUT_DOCX}")


if __name__ == "__main__":
    build_document()
