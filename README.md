# IDE-Embedded DSA Submission Analyzer

A static analysis and behavioral diagnostics system embedded in a student's IDE, designed to extract meaningful learning signals from DSA problem-solving sessions- not just from final submissions, but from the full sequence of attempts, structural edits, and intermediate states that precede them.

---

## Table of Contents

* [Project Overview](#project-overview)
* [Pipeline Architecture](#pipeline-architecture)
* [Approaches Explored](#approaches-explored)
  * [Product Survey](#product-survey)
  * [Intermediate State Capture](#intermediate-state-capture)
  * [Logical Error Detection](#logical-error-detection)
  * [AST Diffing](#ast-diffing)
  * [Graph-Based Code Representations](#graph-based-code-representations)
  * [Submission Analysis and Student Profiling](#submission-analysis-and-student-profiling)
  * [Complexity Metrics](#complexity-metrics)
  * [Visualizations](#visualizations)
* [Work Completed](#work-completed)
* [Work In Progress](#work-in-progress)
* [Roadmap](#roadmap)
* [Setup and Installation](#setup-and-installation)
* [References](#references)

---

## Project Overview

Standard DSA grading treats submission as a binary event- correct or incorrect. What this misses is the entire cognitive process that precedes the final answer: the structural mistakes that repeat across problems, the edit patterns that reveal where understanding breaks down, the misconceptions that persist even when a student eventually arrives at a working solution.

This system captures fine-grained behavioral and structural signals from DSA problem-solving sessions and builds a diagnostic model of how a student *thinks*, not just what they ultimately submit. It operates across two layers:

**Pre-submission analysis**- real-time structural feedback at the problem level: which test cases passed or failed, what error category was hit, complexity of the current solution.

**Longitudinal profiling**- a per-student weakness profile that accumulates signals across sessions and problems, identifying systematic gaps (off-by-one errors that recur across sorting and recursion problems, for example) rather than one-off mistakes.

The broader motivation sits at an inflection point in CS education: under persistent generative AI access, surface-level correctness is no longer a reliable signal of understanding. Students can obtain working solutions trivially. The diagnostic value has shifted almost entirely to the process layer- and that is what this system is built to capture.

---

## Pipeline Architecture

```
IDE Plugin (VS Code Extension)
        |
        v
Event Capture Layer
┌─────────────────────────────────────┐
│  Save events + full source snapshot │
│  Code execution triggers + outcomes │
│  Timestamps (ms resolution)         │
│  Problem identifier (registry)      │
└──────────────┬──────────────────────┘
               |
               v
     AST Extraction (tree-sitter)
     per-snapshot, with error recovery
               |
               v
         AST Diffing Engine
         (structural delta per edit)
               |
       ┌───────┴────────┐
       |                |
       v                v
 XFG Construction   Edit Trajectory
 per snapshot       Encoding
       |                |
       v                |
 Complexity Metrics     |
 (cyclomatic, Halstead, |
  nesting depth,        |
  function length)      |
       |                |
       └───────┬─────────┘
               |
               v
    Student Weakness Profile
    (per-category scores, updated
     per session with decay weighting)
               |
               v
    Feedback + Visualization Layer
    (rules-based feedback,
     per-student and class-wide views)
```

---

## Approaches Explored

### Product Survey

Before building, existing tools were surveyed to identify gaps and avoid reinventing solved problems.

| Tool | Open Source | Relevant Features | Gap |
|---|---|---|---|
| HackerRank / LeetCode | No | Test case evaluation, runtime/memory stats, multi-language support | No process-layer analysis; insights are score summaries and attempt times only |
| CodeGrade | No | Automatic + manual grading, LMS integration, plagiarism checks, line-by-line commenting | Learning insights exist but are tied to the full LMS ecosystem, not IDE-embedded |
| Codio | No | LMS integration, learning insights showing coding vs. debugging time | Insights are rich but require managing full courses through the platform |
| CodeChef for Education / CodeTantra | No | AI coding guide acting as TA, adaptive learning, AI code evaluation | Closed, India-based; no structural error analysis, no longitudinal weakness profiling |
| Python Tutor | Yes | Visualizes call stack, heap, data structure state; AI assistant | Visualization only; no submission analysis or weakness tracking |
| VisualGo / Algorithm Visualizer | Yes / Yes | Algorithm-specific visualizations, custom input | Static visualizers; no student data, no error analysis |
| Debug Visualizer | Yes | Data structure visualization plugin for VS Code | Decoupled architecture is interesting; no analytical layer |
| Algocode | Yes | Monaco editor, Judge0 execution | Simple personal project; no analysis |
| Qingdao Uni OJ | Yes | Rankings, contests | Competition-focused, no learning diagnostics |

**Key finding:** No existing tool operates at the intersection of structural code analysis and longitudinal behavioral profiling inside a student's own IDE. The closest is Codio's learning insights (coding vs. debugging time), but it requires the full Codio LMS. The gap this system fills is real.

**Planned execution engine:** Judge0 (server-side) is the primary candidate. WASI was considered for client-side execution but language and library support constraints make it impractical for the current scope.

---

### Intermediate State Capture

Most existing tools operate on final submissions. This system captures events at save boundaries- a deliberate tradeoff between keystroke-level logging (enormous volume, low per-event signal) and submission-only logging (misses the entire process layer).

Save events approximate natural pause-and-reflect moments. They are frequent enough to capture meaningful edit steps and sparse enough to be non-intrusive.

**What is captured per event:**
- Full source snapshot at each save
- Code execution trigger and stdout/stderr outcome
- Timestamp (millisecond resolution)
- Problem identifier from a problem registry

**Derived metrics from the event sequence:**
- Coding time vs. debugging time (time between first save and first successful run vs. time between runs with errors)
- Number of executions before a correct answer
- Rapid resubmission detection- if a student resubmits within a short window repeatedly, this signals guessing rather than reevaluated reasoning
- Compiler error sequence analysis- multiple consecutive CEs before a runtime error suggests the student is not reading compiler output carefully

---

### Logical Error Detection

Logical errors- code that compiles and runs but produces wrong answers- are the hardest failure class to diagnose. Four approaches from the literature were studied.

#### Subtree-based Attention Neural Network (SANN)

Takes an AST as input and uses a subtree-based attention mechanism to localize logical errors across multiple error categories. No LLM required. The attention weights over subtrees make the localization interpretable- the model surfaces which part of the AST it associates with the error.

*Reference: [arXiv:2505.10913](https://arxiv.org/pdf/2505.10913)*

#### LecPrompt- Perplexity and Log-Probability Based Detection

An LLM trained on correct code identifies where a student's code deviates from what it expects, at the token and line level, via two parameters:

- **Perplexity:** how surprising is this token sequence to the model?
- **Log-probability:** how likely is this token to appear given the surrounding context?

High perplexity / low log-probability at a location flags it as a candidate error site. A separate CodeBERT call then iteratively repairs the flagged region. The recognition stage is the relevant part for this system- the repair stage is out of scope.

*Reference: [arXiv:2410.08241](https://arxiv.org/pdf/2410.08241)*

#### AST Diffing Against Correct Solutions (Watanobe et al.)

ASTs are generated for correct and incorrect submissions to the same problem. The incorrect AST is compared against the most structurally similar correct AST. The diff localizes where the two diverge, which is taken as the candidate error location.

Diffing method: the AST is flattened into a table of element types (variable declaration, if statement, loop, etc.), and error degree is computed using both element types and element content. Each type of difference is assigned a weight.

This approach requires a corpus of correct solutions per problem. For a DSA course context, that corpus can be curated by instructors.

*Reference: [Watanobe et al., ResearchGate](https://www.researchgate.net/profile/Yutaka-Watanobe/publication/336139636_Logic_Error_Detection_System_based_on_Structure_Pattern_and_Error_Degree)*

#### Code-Pseudocode Graph + GNN (Flagged as Suspect)

Constructs a code-pseudocode graph, then applies a Graph Attention Network to identify nodes contributing to logical errors. CodeBERT generates semantic alignment scores on the side.

This paper was flagged during the literature review as suspect: the authors claim the Graph Attention Network forms connections between code and pseudocode representations, but GANs require an input graph- they do not form graphs. The code-pseudocode mapping construction is also not clearly explained. Listed here for completeness but not considered further.

*Reference: [arXiv:2410.21282](https://arxiv.org/pdf/2410.21282)*

#### Behavioral Test Generation

Generates "behavioral tests" targeting specific logical error patterns and runs them against student submissions. Directed graphs are used to visualize and cluster submissions. A neural network component localizes the general area of the logical error with 75–90% accuracy in reported results.

This is closest in spirit to the test-case-labeling approach used in this system's design (see Submission Analysis section below).

*Reference: [Macnish et al., ResearchGate](https://www.researchgate.net/profile/Cara-Macnish/publication/254623401_Machine_Learning_and_Visualisation_Techniques_for_Inferring_Logical_Errors_in_Student_Code_Submissions)*

---

### AST Diffing

The pipeline uses AST-level structural diffing rather than text-level diffing for the core comparison engine.

#### Why AST over text diff

Text diff (Myers algorithm, standard `diff`) is sensitive to whitespace, variable renaming, and formatting changes that carry no semantic signal. A student who renames `i` to `idx` across their entire file produces a large text diff but a near-zero structural delta. AST diffing captures what changed in the program's *structure*- a new loop introduced, a conditional inverted, a recursive call added, a base case missing.

| | Text Diff | AST Diff |
|---|---|---|
| Sensitivity to rename | High (noisy) | Low (clean) |
| Detects structural change | No | Yes |
| Handles incomplete / unparseable code | Yes | Partially |
| Computational cost | Low | Moderate |

#### Parser selection

Four parsers were evaluated in the literature (srcML, JDT, Tree-sitter, ANTLR):

- **JDT**- simplest AST; Java only. Excluded: language-locked.
- **srcML**- varied language support but limited coverage. Excluded: insufficient breadth.
- **ANTLR**- most complex AST; requires language-specific grammar files. Too heavy for the IDE context.
- **Tree-sitter**- language-agnostic incremental parser. Produces ASTs for C, Python, Java, and others from a single unified interface. Supports error recovery on partial/broken code. Selected.

*Reference: [arXiv:2312.00413](https://arxiv.org/pdf/2312.00413)*

#### Handling broken intermediate code

Students frequently write syntactically broken code during active editing. Discarding snapshots that fail to parse would remove exactly the moments where diagnostic signal is richest- the transition states between one structural approach and another. Tree-sitter's error recovery mode extracts partial ASTs from files that don't parse cleanly. Partial ASTs are flagged in the diff output.

#### AST diff tools considered

- **GumTree**- top-down then bottom-up matching; produces edit scripts (insert, delete, move, update operations). Well-established baseline for fine-grained AST diffing.
- **Smartdiff**- open source; diffs two code files at the AST level, supports C and Python. Architecture is relevant; being evaluated.
- **Diaphora**- binary-level diffing tool. Not directly applicable but the diffing strategies are referenced.

*Reference: GumTree- [Falleri et al., ASE 2014](https://dl.acm.org/doi/10.1145/2642937.2642982)*

---

### Graph-Based Code Representations

Beyond AST diffing on individual snapshots, richer graph representations capture control flow, data flow, and execution semantics.

#### Execution Flow Graphs (XFGs)

XFGs encode both control flow and data flow in a single graph, constructed from LLVM's instruction representation. LLVM has native C/C++ support and can compile Python, making XFGs feasible across the languages relevant to this system.

**XFG nodes:** instructions / statements  
**XFG edges:** control flow edges, data dependency edges

The data-dependency edges are the key addition over a plain CFG. A student who writes a loop that iterates correctly but reads the wrong variable at each step produces a structurally valid CFG. The XFG's data edges expose that error class.

*Reference: [arXiv:1806.07336](https://arxiv.org/pdf/1806.07336)*

#### Control Flow Graphs (CFGs)

CFGs from assembly-level C code have been used to predict program behavior and bug presence. funcGNN takes two CFGs constructed from Java programs as input and outputs a similarity score (0 to 1, 1 = identical programs), which is directly applicable to comparing a student's snapshot sequence.

*References:*
- *[arXiv:1802.04986](https://arxiv.org/pdf/1802.04986)*
- *funcGNN- [arXiv:2007.13239](https://arxiv.org/pdf/2007.13239)*

#### Semantic Flow Graphs

Used in SemanticCodeBERT to train a model that, given a bug report, finds the most relevant code changeset. The semantic flow graph itself- not the CodeBERT application- is the relevant component for representing program semantics in this pipeline.

*Reference: [ACM DL](https://dl.acm.org/doi/pdf/10.1145/3611643.3616338)*

#### SigmaDiff- Semantics-Aware Pseudocode Diffing

AI-assisted system that performs semantics-aware diffing between pseudocode representations. Relevant as a potential approach for comparing a student's solution structure against a canonical algorithm description rather than against another student's code.

*Reference: [SMU Institutional Repository](https://ink.library.smu.edu.sg/cgi/viewcontent.cgi?article=9671&context=sis_research)*

#### Why XFGs over CFGs alone / over full PDGs

| Representation | Control Flow | Data Flow | Call Graph | Cost | Usable on Partial Code |
|---|---|---|---|---|---|
| CFG | Yes | No | No | Low | Yes |
| PDG (Program Dependence Graph) | Yes | Yes (precise) | Yes | High | No |
| XFG | Yes | Yes (approximate) | Partial | Moderate | Yes (with recovery) |

PDGs require full program analysis and are not viable for the IDE context where graphs must be recomputed on every save, frequently on partial programs.

---

### Submission Analysis and Student Profiling

#### Test case design for diagnostic value

Test cases are labeled by what they check, so that failure patterns map directly to weakness categories rather than just failure counts:

- **Boundary test cases**- empty input, single element, maxed-out constraints
- **Sorted vs. unsorted input**- catches assumptions about input order
- **Small vs. large input**- flags complexity issues
- **Labeled categories**- off-by-one, overflow, base case, edge case, so a failure graph maps to actual weakness categories rather than anonymous test numbers

#### Per-submission statistics

- Error type distribution- bar chart of error categories (segmentation fault, division by zero, wrong answer, TLE) per problem
- Test case failure heatmap- students × test cases, showing pass/fail/not-reached
- Submission attempt histogram- how many attempts before AC; a bimodal distribution signals a problem with a specific trick that some students identify and others don't
- Rapid resubmission detection- resubmissions within a short window indicate guessing
- CE sequence analysis- multiple consecutive compile errors before a runtime error suggests the student is not reading compiler output

#### Longitudinal weakness profiling

A per-student weakness score for each failure category (off-by-one, edge cases, complexity, compile errors, memory errors, naming quality, nesting depth) is updated after every submission.

**Exponential decay weighting:** recent failures outweigh older ones. A failure from last month does not dominate a failure from a week ago. This keeps the profile current and prevents resolved issues from persisting indefinitely.

**Strength detection:** students who consistently perform well on problems that the broader cohort struggles with are flagged as strong in that concept area.

**Trend tracking:** the profile records whether a student is improving or declining in each weakness category, and marks categories as resolved once the score drops below threshold consistently.

**Rules-based feedback (no AI required):** a rules table maps weakness thresholds to specific actionable messages. Example: if off-by-one score exceeds the high threshold → "Check your loop bounds- is the condition `<n` or `<=n`? Is the last valid index `n-1` or `n`? Test your solution on an array of length 1."

This approach has a pedagogical grounding: one of the key advantages of programming is that students receive immediate, objective feedback about their reasoning. The feedback layer is designed to encourage students to treat debugging as an active investigation rather than a guessing process, and to use their existing knowledge as a starting point for resolving the gap.

---

### Complexity Metrics

#### Time complexity

Inferred statically from the AST- loop nesting depth and recursive call patterns. Coarse but fast.

#### Cognitive complexity vs. cyclomatic complexity

Both are maintainability metrics but capture different things.

**Cyclomatic complexity** counts linearly independent paths through the code. Straightforward to compute from the CFG.

**Cognitive complexity** attempts to measure how hard the code is to understand as a human reader- penalizes nesting more heavily than sequential structures.

Beyond these, two additional metrics are tracked:

**Halstead metrics**- measure vocabulary (number of distinct operators and operands), volume (total size of implementation), and difficulty (how hard the code is to write/understand). Unlike cyclomatic complexity, Halstead captures naming and expression-based complexity rather than control flow.

**Depth of nesting**- how deep the innermost statement sits inside nested loops and conditionals. Nesting beyond 3 levels is a strong indicator that the student is not decomposing the problem into helper functions. Computable directly from the AST without language-specific tooling.

**Function length**- number of statements per function. Very large functions indicate the student is not breaking the problem into sufficient subproblems.

**Variable naming patterns**- analysis of whether names are single-character, vague, or meaningful. Feedback on readability, not just correctness.

#### Tool landscape for complexity analysis

Most existing complexity tools are language- and environment-specific (Code Metrics for JS/TS/Lua in VS Code; Code Complexity by Nikolay Bogdanov for Java/Kotlin/Python in JetBrains). Tree-sitter addresses this at the parsing layer- one analysis pipeline that works across Python, Java, and C from a single interface.

---

## Work Completed

- Product survey across 9 tools (HackerRank, LeetCode, CodeGrade, Codio, CodeChef for Education, CodeTantra, Python Tutor, VisualGo, Debug Visualizer)
- Literature review across logical error detection (SANN, LecPrompt, Watanobe AST diffing, behavioral test generation), AST parsing tool evaluation (srcML, JDT, Tree-sitter, ANTLR), graph-based code representations (XFG, CFG, semantic flow graph, SigmaDiff), and plagiarism detection as reference
- Parser selection: tree-sitter confirmed as the cross-language AST extraction layer
- AST diffing approach: GumTree-style top-down / bottom-up matching; Smartdiff evaluated as a reference implementation
- Execution engine selection: Judge0 (server-side)
- Test case labeling schema: weakness category tags per test case (off-by-one, overflow, base case, edge case, complexity)
- Weakness profile schema: per-category scores with exponential decay weighting
- Rules-based feedback table: initial set covering off-by-one, edge case blindness, nesting depth, compile error patterns
- Complexity metrics plan: cyclomatic complexity, Halstead metrics, nesting depth, function length, variable naming analysis- all computable from the AST

---

## Work In Progress

- VS Code extension scaffolding: save-event capture, snapshot logging, problem registry
- tree-sitter integration for Python and Java with error recovery on broken intermediate code
- AST diffing implementation: GumTree-style edit script generation between snapshot pairs
- XFG construction from parsed snapshots (control flow + approximate data flow via LLVM)
- Weakness profile update logic: ingesting a session's diff output and updating per-category scores
- Visualization prototypes: error distribution bar chart, test case failure heatmap, submission attempt histogram, per-student weakness trend line chart

---

## Roadmap

**Phase 1- Core Analysis Pipeline (current)**  
Complete event capture → AST extraction → AST diffing → XFG construction. Validate that structural deltas are being captured correctly on a set of hand-authored test cases with known error patterns.

**Phase 2- Weakness Profiling**  
Implement per-student weakness score computation with exponential decay. Build the rules-based feedback table. Deploy on a pilot problem set and collect ground truth from instructors.

**Phase 3- Visualizations**  
Student-facing: test case pass/fail view, personal weakness trend over time, strength/weakness summary. Instructor-facing: error distribution per problem, test case failure heatmap, class-wide weakness chart, submission attempt histogram.

**Phase 4- Evaluation**  
Evaluate misconception detection accuracy against instructor-labeled ground truth. Measure whether SLCG-derived signals predict future performance better than correctness-history alone. Human rater agreement on structural-change event labels.

---

## Setup and Installation

```bash
# Install pipeline dependencies
pip install tree-sitter networkx torch numpy

# Install VS Code extension (development mode)
cd plugin && npm install && npm run compile
# Then: F5 in VS Code to launch Extension Development Host

# Run analysis on a captured session directory
python pipeline/run.py --sessions data/sessions/ --output results/
```

---

## References

| Paper | Venue | Link |
|---|---|---|
| SANN- Subtree-based Attention for Logical Errors | 2025 | [arXiv:2505.10913](https://arxiv.org/pdf/2505.10913) |
| LecPrompt- Perplexity-based Error Detection | 2024 | [arXiv:2410.08241](https://arxiv.org/pdf/2410.08241) |
| Watanobe et al.- AST Diffing for Logic Error Detection | 2019 | [ResearchGate](https://www.researchgate.net/profile/Yutaka-Watanobe/publication/336139636_Logic_Error_Detection_System_based_on_Structure_Pattern_and_Error_Degree) |
| Code-Pseudocode GNN | 2024 | [arXiv:2410.21282](https://arxiv.org/pdf/2410.21282) |
| Macnish et al.- Behavioral Tests for Logical Errors | 2004 | [ResearchGate](https://www.researchgate.net/profile/Cara-Macnish/publication/254623401_Machine_Learning_and_Visualisation_Techniques_for_Inferring_Logical_Errors_in_Student_Code_Submissions) |
| AST Parser Comparison (srcML, JDT, Tree-sitter, ANTLR) | 2023 | [arXiv:2312.00413](https://arxiv.org/pdf/2312.00413) |
| XFG Generation via LLVM inst2vec | 2018 | [arXiv:1806.07336](https://arxiv.org/pdf/1806.07336) |
| funcGNN- CFG Similarity via GNN | 2020 | [arXiv:2007.13239](https://arxiv.org/pdf/2007.13239) |
| CFG-based Bug Prediction | 2018 | [arXiv:1802.04986](https://arxiv.org/pdf/1802.04986) |
| SemanticCodeBERT- Semantic Flow Graph | 2023 | [ACM DL](https://dl.acm.org/doi/pdf/10.1145/3611643.3616338) |
| SigmaDiff- Pseudocode Diffing |- | [SMU Repository](https://ink.library.smu.edu.sg/cgi/viewcontent.cgi?article=9671&context=sis_research) |
| Falleri et al.- GumTree Fine-grained AST Diff | ASE 2014 | [ACM DL](https://dl.acm.org/doi/10.1145/2642937.2642982) |
| Common Logical Errors in Learners | NSF | [par.nsf.gov](https://par.nsf.gov/servlets/purl/10329375) |
| LLM vs. Human Debugging | 2024 | [ACM DL](https://dl.acm.org/doi/pdf/10.1145/3636243.3636245) |
| AST-Based vs. Token-Based Neural Networks | 2024 | [ResearchGate](https://www.researchgate.net/publication/385544710_AST-Based_and_Token-Based_Neural_Networks_for_Source_Code_Classification_A_Comparative_Performance_Analysis) |
