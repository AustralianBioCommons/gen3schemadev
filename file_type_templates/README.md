Files in this directory were adapted from various open access data sources

- dummy_vcf -> taken from the VCF specification
- dummy_clinical -> taken from BioDataCatalyst with original filename: `CCDG_13607_B01_GRM_WGS_2019-02-19_chr1.recalibrated_variants.annotated.clinical`
- dummy_cram -> taken from 1000Genomes -> `HG00152.alt_bwamem_GRCh38DH.20150826.GBR.exome.cram`
- dummy_lipids -> taken from Checa et al. 2015 10.1016/j.aca.2015.02.068 supplementary file `3groups.csv`
- dummy_fastq -> taken from 1000Genomes -> `SRR769545_1.fastq.gz`

original cram was filtered like this: 
```shell
samtools view -C -h HG00152.alt_bwamem_GRCh38DH.20150826.GBR.exome.cram chr20 -o dummy_cram.cram
samtools index dummy_cram.cram
samtools view -b -h dummy_cram.cram -o dummy_bam.bam
samtools index dummy_bam.bam
```

The `generate_sizes_and_md5s.py` script calculates the sizes and md5s and saves them as `file_stats.json` which is useful when uploading data to the gen3. It only needs to be re-run if these files change.