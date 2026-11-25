# References

Verification status date: **2026-11-23**. Window for requirement (d): journal articles from IEEE or ScienceDirect, published within the last five years (Nov 2021 or later).

**Rule for everyone (including Claude Code): never invent a bibliographic detail.** Fields marked `CONFIRM` were not captured from the publisher page; open the DOI or URL and fill them in. S09 step 2 covers this.

## A. The five journal references counted for requirement (d)

| # | Citation (IEEE style) | Publisher / journal | Link | Verified | CONFIRM |
|---|---|---|---|---|---|
| [1] | X. Ma, H. Zou, P. He, J. Keung, Y. Li, X. Yu, and F. Sarro, "On the influence of data resampling for deep learning-based log anomaly detection: Insights and recommendations," *IEEE Trans. Softw. Eng.*, vol. 51, no. 1, pp. 243–261, Jan. 2025. | IEEE Transactions on Software Engineering | doi:10.1109/TSE.2024.3513413 | Title, authors, volume, issue, pages, year, DOI (from several indexes plus the paper's own front page) | nothing |
| [2] | M. Landauer, S. Onder, F. Skopik, and M. Wurzenberger, "Deep learning for anomaly detection in log data: A survey," *Machine Learning with Applications*, vol. 12, Art. no. 100470, Jun. 2023. | Elsevier (ScienceDirect) | https://www.sciencedirect.com/science/article/pii/S2666827023000233 | Title, authors, journal, volume, article number, month/year, ScienceDirect PII | DOI (read it off the page) |
| [3] | Y. Lee, J. Kim, and P. Kang, "LAnoBERT: System log anomaly detection based on BERT masked language model," *Applied Soft Computing*, vol. 146, Art. no. 110689, 2023. | Elsevier (ScienceDirect) | doi:10.1016/j.asoc.2023.110689 | Title, authors, journal, DOI; volume and article number come from another paper's reference list | month; confirm volume and article number |
| [4] | X. Ma, J. Keung, P. He, Y. Xiao, X. Yu, and Y. Li, "A semi-supervised approach for industrial anomaly detection via self-adaptive clustering," *IEEE Trans. Ind. Informat.*, 2023. | IEEE Transactions on Industrial Informatics | doi:10.1109/TII.2023.3280246 | Title, authors, journal, year, DOI (from the author preprint) | volume, issue, pages, month |
| [5] | F. Skopik, M. Wurzenberger, G. Höld, M. Landauer, and W. Kuhn, "Behavior-based anomaly detection in log data of physical access control systems," *IEEE Trans. Dependable Secure Comput.*, vol. 20, no. 4, pp. 3158–3175, 2023. | IEEE Transactions on Dependable and Secure Computing | doi:10.1109/TDSC.2022.3197265 (IEEE Xplore document 9852310) | Title, authors, journal, DOI; volume, issue and pages from secondary sources; first published online in 2022 | confirm volume, issue, pages, month |

### What each reference is used for

| # | Use in the report |
|---|---|
| [1] | Class imbalance in log anomaly datasets and why accuracy alone is misleading; justifies reporting per-class and window-level ratios (chapters II, IV.6) |
| [2] | Survey of deep learning on log data: log parsing, encoding of unstructured logs, LSTM-based sequence models (chapters II.1, II.3) |
| [3] | A BGL-evaluated BERT-based, parser-free alternative to our Drain3 + LSTM pipeline; contrast in related work (chapter II.6) |
| [4] | Clustering-based approach for log data; supports using clustering rather than only classification (chapters II.4, II.6) |
| [5] | Unsupervised, sequence-aware analysis of unstructured textual event data; supports the idea of learning "normal behaviour" without labels (chapter II.6) |

### Spare (if one of the five fails verification or the lecturer rejects it)

- *LogDLR: Unsupervised cross-system log anomaly detection through domain-invariant latent representation*, IEEE Trans. Dependable Secure Comput., vol. 22, no. 4, pp. 4456–4471, 2025, doi:10.1109/TDSC.2025.3548050. CONFIRM the author list on IEEE Xplore.

## B. Dataset and background citations (not counted for requirement (d))

- J. Zhu, S. He, P. He, J. Liu, and M. R. Lyu, "Loghub: A large collection of system log datasets for AI-driven log analytics," in *Proc. IEEE Int. Symp. Softw. Rel. Eng. (ISSRE)*, 2023, pp. 355–366. (IEEE conference paper; published 9 Oct 2023; the arXiv v3 is dated 13 Sep 2023.) Cite the IEEE ISSRE 2023 version, not the 2020 arXiv v1.
- A. Oliner and J. Stearley, "What supercomputers say: A study of five system logs," in *Proc. IEEE/IFIP Int. Conf. Dependable Syst. Netw. (DSN)*, 2007, pp. 575–584. (Origin of the BGL logs and alert tags.)
- Background, well known, CONFIRM details before citing: P. He, J. Zhu, Z. Zheng, and M. R. Lyu, "Drain: An online log parsing approach with fixed depth tree," ICWS 2017; M. Du, F. Li, G. Zheng, and V. Srikumar, "DeepLog: Anomaly detection and diagnosis from system logs through deep learning," ACM CCS 2017.

## C. Citation style

Use IEEE numeric style in the report ([1], [2], ...) in order of first appearance. The order in section A is a convenience; renumber to match the report.

## D. Open question for the humans

The lecturer asked for international **journals** from IEEE or ScienceDirect. All five references in section A are journal articles. The dataset paper (Loghub) is an IEEE conference paper and is cited only as the dataset source.
