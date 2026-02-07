# Building an FPGA Synthesis Tool from Scratch

A complete engineering reference for designing and implementing a hardware synthesis pipeline that transforms HDL source code into an FPGA bitstream.

---

## 1. The Big Picture: What Synthesis Actually Does

An FPGA synthesis tool converts a high-level hardware description (Verilog, VHDL, or a custom HDL) into a configuration bitstream that programs an FPGA's physical resources. The pipeline is a series of graph-to-graph transformations — you are essentially building a compiler where the "instruction set" is a sea of configurable logic blocks, and nearly every intermediate representation is a graph.

**High-Level Pipeline:**

```
HDL Source → [Parsing] → AST
  → [Elaboration] → Design Hierarchy
  → [RTL Synthesis] → RTL Netlist (DAG)
  → [Logic Optimization] → Optimized Boolean Network (AIG / MIG)
  → [Technology Mapping] → Mapped Netlist (DAG of LUTs, FFs, carry chains)
  → [Packing] → Clustered Netlist
  → [Placement] → Placed Netlist (Graph Embedding onto a Grid)
  → [Routing] → Routed Design (Path-finding on a Routing Resource Graph)
  → [Bitstream Generation] → Binary Configuration File
```

Every arrow above is a graph transformation, and understanding that is the single most important conceptual foundation for this project.

---

## 2. Frontend: Parsing and Elaboration

### 2.1 HDL Parser

You need a parser for at least a synthesizable subset of an HDL. Your options:

- **Verilog / SystemVerilog subset** — The most practical choice. You don't need to support the full language; focus on the synthesizable subset (modules, always blocks, assign statements, generate blocks).
- **Custom HDL** — Simpler to implement, lets you skip the gnarly corners of Verilog, but limits your user base.
- **RTLIL (Yosys IR)** — You can skip the parser entirely and consume Yosys's intermediate representation, letting Yosys handle the frontend.

**What you need to build or integrate:**

| Component | Purpose | Suggested Tools / Libraries |
|---|---|---|
| Lexer | Tokenize HDL source | Flex, re2c, or hand-written |
| Parser | Build an Abstract Syntax Tree (AST) | Bison, ANTLR, tree-sitter, or recursive descent |
| AST data structure | Tree representation of source | Custom structs/classes |
| Semantic analysis | Type checking, width inference, parameter resolution | Custom passes over the AST |

### 2.2 Elaboration

Elaboration unrolls the design hierarchy — resolving parameters, expanding generate statements, and flattening the module tree into a single concrete design. The output is typically a **hierarchical netlist** or a **flattened netlist**.

**Graph Theory Connection:** The design hierarchy is a *tree* (a connected acyclic graph). Elaboration performs a depth-first traversal of this tree, instantiating each module with its resolved parameters. Flattening collapses this tree into a single-level graph (the netlist).

**Key tasks:**

- Parameter and `localparam` resolution (constant propagation)
- Generate-block unrolling (loop unrolling on the tree)
- Memory and array inference
- Multi-driven net resolution
- Black-box identification (modules with no body, e.g., vendor primitives)

---

## 3. RTL Netlist and Intermediate Representations

### 3.1 The Netlist as a Graph

The core data structure of your entire tool is the **netlist** — a **directed acyclic graph (DAG)** where:

- **Nodes** represent logic operations (AND, OR, MUX, adder, flip-flop, etc.)
- **Edges** represent wires / signal connections between operations
- **Hyperedges** are common: a single output net can fan out to multiple inputs, making this technically a *directed hypergraph*

You will need a robust, general-purpose graph data structure that supports:

- Efficient node/edge insertion and deletion (you'll do millions of local rewrites)
- Fanin/fanout traversal (given a node, quickly iterate its drivers and its loads)
- Topological ordering (critical for forward/backward dataflow analysis)
- Subgraph extraction and replacement

**Recommended representations:**

| Representation | Pros | Cons |
|---|---|---|
| Adjacency list (node → list of edges) | Flexible, easy to mutate | Pointer chasing, cache-unfriendly |
| Compressed edge array (like CSR) | Cache-friendly traversal | Expensive mutation |
| Hybrid (adjacency list + node pool allocator) | Good balance | More complex implementation |

### 3.2 Common IRs in Synthesis

- **RTLIL** — Yosys's IR. Word-level, supports memories, processes, cells. Well-documented.
- **AIG (And-Inverter Graph)** — A DAG where every node is a 2-input AND gate and edges may be complemented (inverted). Extremely compact and canonical. The workhorse of modern logic optimization (see ABC tool).
- **MIG (Majority-Inverter Graph)** — Each node is a 3-input majority function. Offers better optimization for some circuits.
- **XAG (XOR-AND Graph)** — Adds XOR as a native node type; useful for arithmetic-heavy designs.
- **LUT Network** — A DAG of k-input lookup tables. The target representation for FPGA mapping.
- **Mapped Netlist** — A DAG of vendor-specific primitives (LUT4, CARRY4, BRAM, DSP, IO buffers).

**Graph Theory Connection:** An AIG is a *DAG with bounded in-degree* (every node has exactly 2 inputs). Structural hashing ensures the AIG is *canonical up to local structure*: if two nodes compute the same function of the same inputs, they are merged (this is graph deduplication). The AIG can be viewed as a compact representation of a Boolean function's circuit complexity.

---

## 4. Logic Optimization

This is where the core algorithmic difficulty lives. You are transforming a Boolean network (a DAG of logic functions) into a smaller, faster equivalent network.

### 4.1 Two-Level Optimization (Combinational)

Classical Boolean minimization of individual functions:

- **Quine-McCluskey** — Exact; exponential in the number of variables
- **Espresso** — Heuristic two-level minimizer; fast and practical
- Useful for collapsing small cones of logic, but not the primary optimization strategy for FPGAs

### 4.2 Multi-Level Optimization (the main event)

Operates on the netlist graph as a whole, applying local and global transformations.

**Key algorithms and their graph-theoretic foundations:**

| Technique | Graph Theory Basis | Description |
|---|---|---|
| **Structural hashing** | Node equivalence / graph isomorphism (local) | Merge nodes with identical function and identical fanin. Hash each node by (operation, sorted input IDs). |
| **Constant propagation** | Reachability analysis | Identify nodes with constant outputs and propagate, removing dead edges. |
| **Dead logic removal** | Reverse reachability from primary outputs | BFS/DFS backward from outputs; any unreachable node is dead and can be deleted. |
| **Common subexpression elimination** | Subgraph isomorphism (local) | Find identical sub-DAGs and merge them into one. |
| **AIG rewriting** | Local subgraph replacement / graph rewriting | Enumerate all k-input cuts of each node, find optimal implementations using precomputed NPN classes, replace subgraphs. This is the core of ABC's `rewrite` command. |
| **AIG refactoring** | Cone extraction + resynthesis | Extract the Boolean function for a logic cone (the *transitive fanin* subgraph), resynthesize with a better structure. |
| **AIG balancing** | Tree balancing | Restructure associative operator chains (AND, XOR) into balanced trees to minimize DAG depth (critical path). |
| **Retiming** | Min-cost flow on a graph | Move flip-flops across combinational logic to balance pipeline stages. Modeled as a flow problem on the netlist graph where registers are weights on edges. |
| **FSM optimization** | State graph minimization | Extract finite state machines, minimize states (graph partitioning / bisimulation), re-encode. |
| **Don't-care optimization** | Satisfiability, observability | Compute sets of input conditions that cannot occur (SDC) or whose output values don't matter (ODC). Use these to further simplify node functions. |

**Graph Theory Connection — Cuts and Cones:** A *k-feasible cut* of a node `v` in a DAG is a set of nodes `C` such that every path from a primary input to `v` passes through at least one node in `C`, and `|C| ≤ k`. The subgraph between the cut `C` and `v` is the *cone*. Enumerating cuts is a fundamental DAG operation — it partitions the graph into overlapping subgraphs, each representing a Boolean function of at most `k` variables. This directly feeds technology mapping.

### 4.3 Equivalence Checking

After optimization, you need to verify the optimized netlist is functionally equivalent to the original. Techniques:

- **SAT-based combinational equivalence checking (CEC)** — Construct a *miter* (XOR the outputs of the two circuits, OR all miter outputs). If the resulting formula is unsatisfiable, the circuits are equivalent.
- **Simulation-based** — Random simulation for quick counterexample finding.
- **BMC (Bounded Model Checking)** — For sequential equivalence.

---

## 5. Technology Mapping

Technology mapping converts a generic Boolean network (typically an AIG) into a netlist of FPGA-specific primitives — primarily **k-input Look-Up Tables (LUTs)**.

### 5.1 LUT Mapping

This is a **graph covering** problem:

> Given a DAG (the AIG), cover every node with a set of k-feasible cuts such that every primary output is covered, optimizing for area (number of LUTs), delay (depth of the mapped network), or a combination.

**Algorithms:**

| Algorithm | Strategy |
|---|---|
| **FlowMap** | Optimal-depth LUT mapping using network flow. Models the problem as a series of max-flow / min-cut problems on the AIG. |
| **CutMap / DAOmap** | Area-oriented mapping using cut enumeration and dynamic programming on the DAG. |
| **ABC's `if` command** | Industrial-strength mapper combining cut enumeration, priority cuts, and area recovery. |
| **Chortle** | Tree-based decomposition for LUT mapping. |

**Graph Theory Connection — FlowMap and Min-Cut:** FlowMap computes the minimum-depth LUT mapping by solving a max-flow / min-cut problem for each node. For a node `v` at the intended depth `d`, it finds a minimum-cost cut separating `v` from all nodes at depth `d - k` or below. By the max-flow min-cut theorem, this gives the smallest set of LUT inputs needed. This is a beautiful application of flow theory to synthesis.

### 5.2 Carry Chain Inference

FPGA carry chains are hardwired fast-carry paths. Your mapper needs to recognize adder/subtractor/comparator patterns in the AIG and map them to carry chain primitives instead of generic LUTs. This is a form of **subgraph pattern matching** on the netlist.

### 5.3 Memory Mapping

Infer block RAMs (BRAMs) and distributed RAMs from arrays in the design. Requires pattern matching for read/write port structures and address decoding logic.

### 5.4 DSP Mapping

Recognize multiply-accumulate (MAC) patterns and map them to DSP hard blocks. Again, subgraph pattern matching.

---

## 6. Packing

Packing groups the mapped primitives (LUTs, flip-flops, carry chains) into the FPGA's physical **Configurable Logic Blocks (CLBs)** or **Logic Array Blocks (LABs)**.

**Graph Theory Connection:** Packing is a **graph clustering** or **graph partitioning** problem. You want to group tightly connected nodes together (to minimize inter-cluster routing) while respecting the physical constraints of each cluster (e.g., a Xilinx CLB slice contains 4 LUT6s, 8 flip-flops, carry chain, and muxes).

**Algorithms:**

- **Greedy seed-based packing** — Pick a seed LUT, greedily absorb connected FFs and LUTs that share inputs. (T-VPack, AAPack)
- **ILP-based packing** — Formulate as an integer linear program for optimal results on small designs.
- **Simulated annealing** — Used in some packers for quality.

**Legality checks at this stage:**

- Number of distinct inputs to a cluster ≤ cluster input count
- FF control set compatibility (same clock, reset, enable)
- Carry chain continuity

---

## 7. Placement

Placement assigns each packed cluster to a physical location on the FPGA grid. This is where your algorithm meets the physical chip.

### 7.1 Problem Formulation

**Graph Theory Connection:** Placement is a **graph embedding** problem — you are embedding the netlist graph into a 2D grid graph (the FPGA fabric) such that the total weighted edge length (wirelength) is minimized. This is closely related to the **quadratic assignment problem** (QAP), which is NP-hard.

### 7.2 Algorithms

| Algorithm | Description |
|---|---|
| **Simulated Annealing (SA)** | The gold standard for FPGA placement (used by VPR). Randomly swap/move clusters, accept moves based on a cost function and temperature schedule. Slow but high quality. |
| **Analytical Placement** | Formulate as a quadratic optimization problem (minimize sum of squared wirelength), solve with conjugate gradient, then legalize. Faster than SA for large designs. Used in modern ASIC placers (ePlace, RePlAce). |
| **Min-Cut Partitioning** | Recursively partition the netlist using min-cut (Kernighan-Lin, Fiduccia-Mattheyses) and assign partitions to chip quadrants. |
| **Force-Directed Placement** | Model nets as springs, simulate the physical system to equilibrium. |

**Cost function components:**

- **Wirelength estimate** — Half-perimeter wirelength (HPWL) of bounding boxes for each net
- **Timing** — Weighted wirelength based on criticality (from static timing analysis)
- **Congestion** — Penalize areas with too many nets passing through (estimated by probabilistic routing models)

### 7.3 The FPGA Grid Model

You need a data structure representing the physical FPGA:

- A 2D grid of **tiles**, each containing one or more **sites**
- Site types: CLB, BRAM, DSP, IOB, clock regions
- Constraints: certain blocks can only go in certain site types
- Fixed locations: I/O pins are often pre-assigned

---

## 8. Routing

Routing assigns physical wires to every net in the placed design. This is the most computationally expensive stage and heavily relies on graph algorithms.

### 8.1 The Routing Resource Graph (RRG)

The FPGA's routing fabric is modeled as a **directed graph** called the **Routing Resource Graph**:

- **Nodes** represent physical routing resources: wire segments, switch block multiplexers, connection block inputs/outputs, pin access points
- **Edges** represent configurable connections between resources (pass transistors, multiplexers, buffers)
- **Edge weights** encode delay, capacitance, and congestion cost

For a modern FPGA, this graph can have **tens of millions of nodes** and **hundreds of millions of edges**. Efficient graph storage and traversal is absolutely critical.

### 8.2 Routing Algorithms

| Algorithm | Description |
|---|---|
| **PathFinder (negotiated congestion)** | The standard FPGA routing algorithm. Routes all nets simultaneously, allowing initial congestion, then iteratively rips up and reroutes nets with increasing congestion penalties until all congestion is resolved. Each net is routed using Dijkstra's shortest path on the RRG. |
| **A\* search** | Variant of Dijkstra with a heuristic (Manhattan distance to target) for faster individual net routing. |
| **Maze routing (Lee's algorithm)** | BFS on a grid; conceptually simple but slow. Useful for understanding. |
| **SAT/ILP-based routing** | Exact formulation for small designs or critical nets. |

**Graph Theory Connection — PathFinder:** PathFinder is an iterative application of **shortest-path algorithms** on a weighted graph with dynamically updated edge weights. The congestion penalty on each RRG node increases each iteration proportional to how over-used the node is. This is essentially a form of **Lagrangian relaxation** applied to a multi-commodity flow problem on a graph — each net is a "commodity" that must flow from source to sinks through the RRG.

### 8.3 Timing-Driven Routing

Nets on the critical path get priority and lower-cost edges in the RRG. This requires tight integration with static timing analysis (see below).

---

## 9. Static Timing Analysis (STA)

STA computes the delay of every path through the design to determine if timing constraints are met.

**Graph Theory Connection:** STA operates on the **timing graph**, a DAG where:

- Nodes are **timing points** (pins of cells)
- Edges are **timing arcs** with associated delays (cell delays, wire delays)
- **Arrival time** at each node is computed by a **longest-path** computation (topological-order traversal, taking the max incoming arrival time + arc delay at each node)
- **Required time** is propagated backward from output constraints
- **Slack** = required time - arrival time; negative slack means a timing violation

The critical path is the **longest path** in the timing DAG — a fundamental graph problem solvable in O(V + E) time on a DAG via topological sort.

STA feeds back into placement and routing: net criticality values guide the optimizer to focus effort on timing-critical paths.

---

## 10. Bitstream Generation

The final stage: convert the placed-and-routed design into a binary bitstream that programs the FPGA.

**What you need:**

- A complete model of the FPGA's configuration memory (which bits control which resources)
- For each placed cell: determine the LUT truth table bits, FF configuration bits, mux select bits
- For each routed net: determine which routing switches to enable (which bits in the switch matrix to set)
- Frame assembly: organize bits into the FPGA's configuration frame format
- CRC/ECC: add error-checking codes as required by the device

**This is the most device-specific part of the tool.** For open-source efforts:

| FPGA Family | Bitstream Documentation |
|---|---|
| Lattice iCE40 | Fully reverse-engineered (Project IceStorm) |
| Lattice ECP5 | Fully reverse-engineered (Project Trellis) |
| Xilinx 7-Series | Partially reverse-engineered (Project X-Ray) |
| Gowin | Partially reverse-engineered (Project Apicula) |
| Intel/Altera | Not publicly documented |

---

## 11. FPGA Architecture Model

Your tool needs a formal description of the target FPGA. This is an extensive data model:

### 11.1 Architecture Description

- **Logic block architecture** — How many LUTs per cluster, their sizes (k), number of FFs, local routing, carry chains
- **Routing architecture** — Wire segment types and lengths, switch block topology (Wilton, Universal, Subset), connection block patterns
- **I/O architecture** — IOB types, voltage standards, pin locations
- **Hard blocks** — BRAM size/configuration, DSP capabilities, PLL/MMCM locations
- **Clock network** — Global clock buffers, regional clocks, clock regions

### 11.2 Architecture Formats

- **VPR Architecture XML** — The most established open format. VPR (Verilog-to-Routing) uses an XML file describing the entire FPGA architecture, including routing graph generation parameters.
- **FPGA Interchange Format (FPGAIF)** — A newer effort by Google/SymbiFlow to standardize architecture descriptions across tools.

---

## 12. Essential Supporting Infrastructure

### 12.1 SAT Solver

You will need a SAT solver for equivalence checking, optimization, and possibly routing. Options: MiniSat, CaDiCaL, Kissat, or integrate via the IPASIR interface.

### 12.2 BDD Library

Binary Decision Diagrams for representing and manipulating Boolean functions compactly. Useful in don't-care computation and FSM analysis. Options: CUDD, Sylvan.

### 12.3 Static Timing Analysis Engine

A dedicated STA module that operates on the timing graph and provides arrival times, required times, and slack to every other stage of the tool.

### 12.4 SDC Parser

Synopsys Design Constraints (SDC) is the standard for timing constraints (`create_clock`, `set_input_delay`, `set_false_path`, etc.). You need a parser for at least a subset of SDC/Tcl.

### 12.5 Standard File Formats

| Format | Purpose |
|---|---|
| **Verilog / BLIF / EBLIF** | Netlist interchange |
| **SDF** | Standard Delay Format (timing annotation) |
| **SDC** | Timing constraints |
| **EDIF** | Legacy netlist format |
| **VPR Architecture XML** | FPGA architecture description |
| **FASM (FPGA Assembly)** | Human-readable bitstream representation |
| **PCF** | Pin constraint file |

---

## 13. Graph Theory Concepts Summary

A consolidated reference of the graph theory that underpins FPGA synthesis:

| Concept | Where It Appears |
|---|---|
| **DAG (Directed Acyclic Graph)** | Netlists, AIGs, timing graphs — the fundamental data structure throughout |
| **Topological Sort** | Levelization for optimization, STA forward/backward passes |
| **Longest Path (in a DAG)** | Critical path / static timing analysis |
| **Shortest Path (Dijkstra, A\*)** | Signal routing on the routing resource graph |
| **Max-Flow / Min-Cut** | Technology mapping (FlowMap), partitioning-based placement |
| **Graph Partitioning** | Placement (Kernighan-Lin, FM), packing |
| **Graph Coloring** | Register allocation, resource binding in HLS |
| **Graph Embedding** | Placement (embedding netlist graph into physical grid graph) |
| **Subgraph Isomorphism** | Pattern matching for carry chains, DSP blocks, CSE |
| **Graph Rewriting** | AIG rewriting, local optimization passes |
| **Hypergraph** | Netlist representation (nets with fanout > 1) |
| **Multi-Commodity Flow** | Routing (each net is a commodity in the RRG) |
| **Tree Decomposition** | Cut enumeration, treewidth-based exact methods |
| **DFS / BFS Traversal** | Dead logic removal, cone extraction, connectivity analysis |
| **Strongly Connected Components** | Combinational loop detection (SCCs in a netlist → illegal) |
| **Bipartite Matching** | Clock/reset assignment, resource binding |

---

## 14. Open-Source Tools to Study and Build On

Do not build everything from scratch. Study and potentially integrate these:

| Tool | What It Does | License |
|---|---|---|
| **Yosys** | RTL synthesis, optimization, technology mapping | ISC |
| **ABC** | AIG-based logic optimization and mapping | BSD |
| **VPR (Verilog-to-Routing)** | Packing, placement, routing, STA, architecture modeling | MIT |
| **nextpnr** | Place-and-route for iCE40, ECP5, Gowin, Nexus | ISC |
| **Project IceStorm** | iCE40 bitstream tools | ISC |
| **Project Trellis** | ECP5 bitstream tools | ISC |
| **GHDL** | VHDL frontend (can output to Yosys) | GPL |
| **Surelog/UHDM** | SystemVerilog parser and elaborator | Apache 2.0 |
| **OpenROAD** | ASIC PnR (analytical placement, global routing — concepts transfer) | BSD |

---

## 15. Suggested Implementation Roadmap

### Phase 1 — Learn the Pipeline (Weeks 1–4)
- Install Yosys + nextpnr + IceStorm. Synthesize a blinking LED for iCE40. Trace the entire flow.
- Read the VPR and ABC documentation thoroughly.
- Implement a basic netlist graph data structure with topological sort.

### Phase 2 — Build a Toy Frontend (Weeks 5–8)
- Parse a tiny subset of Verilog (wire/reg declarations, assign, always @(posedge clk), basic operators).
- Elaborate into a flat netlist DAG.
- Export to BLIF for verification against Yosys.

### Phase 3 — Logic Optimization (Weeks 9–14)
- Implement AIG construction from the netlist.
- Implement structural hashing, constant propagation, dead node removal.
- Implement cut enumeration (k-feasible cuts).
- Study and implement a basic AIG rewrite pass.

### Phase 4 — Technology Mapping (Weeks 15–18)
- Implement LUT mapping via cut enumeration + dynamic programming.
- Target iCE40 LUT4s as the simplest starting point.
- Verify mapped netlists against original using simulation.

### Phase 5 — Place and Route (Weeks 19–28)
- Build or import the iCE40 architecture model and RRG.
- Implement simulated annealing placement.
- Implement PathFinder routing.
- Implement basic STA.

### Phase 6 — Bitstream Generation (Weeks 29–32)
- Use Project IceStorm's bitstream documentation to generate iCE40 bitstreams.
- Test on real hardware.

### Phase 7 — Iterate and Optimize (Ongoing)
- Profile and optimize critical algorithms.
- Add timing-driven placement and routing.
- Support more FPGA architectures.
- Add equivalence checking.

---

## 16. Recommended Reading

- **"Logic Synthesis and Verification Algorithms"** — Hachtel & Somenzi
- **"Synthesis and Optimization of Digital Circuits"** — De Micheli
- **"FPGA Place and Route Challenge"** — ISPD contest papers
- **"Technology Mapping for FPGAs"** — Cong & Ding (FlowMap paper)
- **"PathFinder: A Negotiation-Based Performance-Driven Router"** — McMurchie & Ebeling
- **"DAOmap: A Depth-Optimal Area Optimization Mapping Algorithm for FPGA Designs"** — Chen & Cong
- **"ABC: A System for Sequential Synthesis and Verification"** — Berkeley
- **"Architecture and CAD for Deep-Submicron FPGAs"** — Betz, Rose & Marquardt (the VPR book — essential reading)

---

*This is a living document. Each section above could expand into its own detailed specification as you progress through implementation.*
