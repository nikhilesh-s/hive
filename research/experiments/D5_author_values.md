# D5 (second half) — author-value comparison feasibility at v0.3.0 gates

Question: can HiveBlot's within-image relative reading be compared with the LC3B-II:ACTB ratios the BEX2 paper publishes as bar charts? A pair needs the LC3B strip AND the ACTB strip of the same panel to pass the clipping gate. Diagnostic geometry (detected rows, auto lanes); `scripts/experiments/densitometry_author_values.py`.

| crop | detected rows | rows not refused | max clipped core per row (first 8) |
|---|---|---|---|
| page_004_cand_0025.png | 11 | 3 | 620-661: 93%, 278-319: 100%, 517-553: 91%, 394-420: 64%, 155-164: 90%, 335-343: 100%, 252-259: 100%, 678-684: 100% |
| page_005_cand_0032.png | 13 | 0 | 650-736: 94%, 390-464: 95%, 805-853: 70%, 537-575: 100%, 476-504: 100%, 593-603: 100%, 624-632: 100%, 609-616: 81% |
| page_006_cand_0037.png | 10 | 1 | 567-615: 51%, 285-319: 51%, 394-421: 24%, 453-475: 15%, 633-640: 32%, 529-536: 4%, 349-356: 17%, 247-254: 17% |
| page_006_cand_0039.png | 14 | 0 | 713-751: 49%, 341-383: 27%, 465-507: 46%, 604-634: 26%, 552-559: 29%, 525-532: 29%, 539-545: 0%, 669-675: 0% |
| page_006_cand_0040.png | 5 | 0 | 338-382: 38%, 710-745: 66%, 610-634: 28%, 417-421: 0%, 427-530: 12% |
| page_007_cand_0045.png | 8 | 5 | 433-515: 19%, 790-832: 33%, 562-604: 28%, 679-714: 21%, 422-429: 37%, 537-544: 7%, 619-626: 7%, 734-741: 7% |
| page_007_cand_0046.png | 7 | 1 | 334-397: 41%, 791-821: 54%, 653-669: 33%, 301-310: 23%, 556-565: 0%, 413-419: 20%, 441-541: 17% |
| page_009_cand_0055.png | 9 | 1 | 400-484: 11%, 926-976: 40%, 675-723: 50%, 799-842: 27%, 1211-1249: 62%, 552-593: 30%, 1097-1120: 17%, 296-315: 60% |
| page_010_cand_0060.png | 9 | 1 | 584-640: 46%, 713-763: 49%, 448-492: 28%, 988-1024: 56%, 330-360: 50%, 878-905: 25%, 424-431: 3%, 651-657: 33% |
| page_010_cand_0062.png | 7 | 0 | 423-489: 29%, 823-883: 24%, 690-737: 42%, 963-1003: 60%, 299-342: 25%, 565-599: 27%, 493-499: 38% |

**Result: n too small.** 12 of 93 detected rows on these 10 crops pass the gates, and no crop has two passing rows that could be an LC3B / ACTB pair (the ACTB loading-control strips are the most clipped rows in the paper). A comparison against the authors' bar charts is therefore not possible from the published figures at these gates; it needs the raw exposures (ticket D-7). This is the expected, honest outcome and is not a defect of the gates.

Not done: reading the bar-chart values themselves. They would have nothing to be compared with.
