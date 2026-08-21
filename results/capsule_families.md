# Capsule families, and what they imply about cost

No per-capsule compute data is published. The paper reports only 4.2 hours total
(Table 1) and no token counts, and the 530 trajectories were never released, so
cost has to be inferred from capsules already run here.

Question length failed as a predictor: bix-4 has the shortest questions of any
capsule and cost the most. What does carry signal is **family** -- capsules built
from the same source paper share input data and analysis style, so a measured cost
on one bounds its siblings.

Measured anchors, per replica at `max_steps: 40`:

| Capsule | Cost | Actions used |
|---|---:|---|
| bix-8 | $1.35 | 9, 9, 9, 11, 11, 14 |
| bix-53 | $2.86 | 14, 17, 20, 20, 20 |
| bix-43 | $3.22 | 17, 18, 20, 20, 20 |
| bix-4 | $7.62 | 15, 16, 16, 19, 20, 26, 40 |

=== genuine families (shared source paper) ===
   7  bix-13, bix-18, bix-26, bix-32, bix-41, bix-46, bix-54 
   4  bix-1, bix-5, bix-14, bix-49                     
   4  bix-7, bix-17, bix-39, bix-47                    
   3  bix-22, bix-31, bix-36                           
   2  bix-10, bix-29                                   
   2  bix-2, bix-20                                    
   2  bix-24, bix-43                                   bix-43=$3.22
   2  bix-3, bix-9                                     
   2  bix-8, bix-37                                    bix-8=$1.35

=== unlabeled capsules, clustered by hypothesis topic ===
  fungi-vs-animals    7  bix-4, bix-11, bix-12, bix-21, bix-35, bix-38, bix-45  bix-4=$7.62
  other-unlabeled    10  bix-16, bix-25, bix-28, bix-34, bix-51, bix-55, bix-56, bix-57, bix-58, bix-60  
  bacteria/AMR        1  bix-61  
