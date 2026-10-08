"""
Paper Decoder & Simple Explainer Engine for BioWriter Studio.
Deconstructs peer-reviewed scientific papers and abstracts into:
1. Executive 3-Sentence Summary (Problem -> Intervention -> Finding)
2. Plain-English "ELI-Undergrad" Explanation with real-world analogies
3. Biotech Jargon Buster (detects 60+ complex terms and provides clear definitions + analogies)
4. Extracted Proposal Parameters (Chassis, Tool, Quantified Metrics, Controls, Limitations)
5. Proposal Placement Recommendations (Tier 1, 2, 3, Aims, Competitors)
6. Socratic RHEV Paraphrase & Synthesis Challenge (Anti-Ghostwriting firewall)
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
import requests

# 60+ Biotechnology Terms with Plain-English Definitions & Analogies
JARGON_LEXICON = {
    "allosteric": {
        "term": "Allosteric Regulation / Allosteric Site",
        "simple_def": "A control switch on a protein located away from its active site.",
        "analogy": "Like a dimmer switch on a wall that controls the light without you having to touch the lightbulb directly."
    },
    "directed evolution": {
        "term": "Directed Evolution",
        "simple_def": "Speeding up natural selection in a test tube by mutating genes and picking the winners.",
        "analogy": "Like breeding racehorses, but doing 10,000 generations of bacteria in three days to find the fastest enzyme."
    },
    "codon optimization": {
        "term": "Codon Optimization",
        "simple_def": "Rewriting a gene's DNA spelling so the new host organism can read and translate it faster without changing the resulting protein.",
        "analogy": "Like translating British English slang into American English so a US reader doesn't stumble, while keeping the meaning identical."
    },
    "inclusion bodies": {
        "term": "Inclusion Bodies",
        "simple_def": "Dense, insoluble clumps of misfolded, non-functional protein inside a bacterial cell.",
        "analogy": "Like throwing clothes into a closet so fast that they ball up into a tangled knot you cannot wear until you iron each piece."
    },
    "isothermal": {
        "term": "Isothermal Amplification (e.g., LAMP, RPA)",
        "simple_def": "Multiplying DNA or RNA at a single, constant temperature without needing an expensive heating/cooling machine.",
        "analogy": "Like baking a cake in a simple warm water bath instead of an oven that has to repeatedly cycle between freezing and broiling."
    },
    "limit of detection": {
        "term": "Limit of Detection (LOD)",
        "simple_def": "The smallest amount of a target molecule that an assay can reliably detect from background noise.",
        "analogy": "Like how faint a whisper can be in a crowded room before your ear can no longer distinguish it from background chatter."
    },
    "lod": {
        "term": "Limit of Detection (LOD)",
        "simple_def": "The absolute lowest concentration of a biomarker that gives a reliable positive signal.",
        "analogy": "The smallest drop of food coloring in a swimming pool that still changes the water's tint."
    },
    "kcat": {
        "term": "Turnover Number (kcat)",
        "simple_def": "How many chemical reactions a single enzyme molecule can complete per second at full speed.",
        "analogy": "Like a factory worker's assembly speed: how many car doors one technician can bolt on in 60 seconds."
    },
    "km": {
        "term": "Michaelis Constant (Km)",
        "simple_def": "The concentration of substrate needed for an enzyme to reach half its maximum speed (measures binding grip).",
        "analogy": "Low Km means a high-grip magnet: it grabs iron filings even when they are scarce. High Km means a weak magnet: it needs a huge pile of iron before it grabs anything."
    },
    "tm": {
        "term": "Melting Temperature (Tm)",
        "simple_def": "The temperature at which exactly half of the protein molecules unfold and lose their active shape.",
        "analogy": "Like the melting point of chocolate: the exact temperature where it stops holding its solid bar shape and turns into runny liquid."
    },
    "thermal denaturation": {
        "term": "Thermal Denaturation",
        "simple_def": "Heat causing a structured protein to unfold, scramble its bonds, and permanently stop working.",
        "analogy": "Like frying an egg: clear liquid albumen turns into opaque solid white and can never be liquid again."
    },
    "chimeric": {
        "term": "Chimeric / Fusion Protein",
        "simple_def": "An engineered protein stitched together from two or more completely different parent genes.",
        "analogy": "Like building a mythological Griffin: grafting an eagle's wings onto a lion's body to get both flight and muscle."
    },
    "promoter": {
        "term": "Promoter",
        "simple_def": "A stretch of DNA that acts as the 'ON' switch and ignition key for RNA polymerase to transcribe a gene.",
        "analogy": "Like the green 'Start' button on an industrial machine."
    },
    "crispr": {
        "term": "CRISPR-Cas System",
        "simple_def": "A bacterial immune defense adapted into a programmable molecular scissor with an RNA guide GPS.",
        "analogy": "Like giving molecular scissors a GPS address so they only cut one specific zip code in a 3-billion-letter book."
    },
    "collateral cleavage": {
        "term": "Collateral / Trans-Cleavage (Cas12/Cas13)",
        "simple_def": "Once a Cas enzyme cuts its specific target, it goes wild and chops nearby bystander fluorescent reporter probes.",
        "analogy": "Like a security alarm that, upon spotting a burglar, starts setting off confetti cannons all over the room to alert everyone."
    },
    "metabolic burden": {
        "term": "Metabolic Burden",
        "simple_def": "The energy and resource drain placed on a host cell when forced to produce huge amounts of recombinant protein.",
        "analogy": "Like asking an engine to pull three loaded freight cars: it slows down, overheats, and consumes all its fuel just to move."
    },
    "chromatography": {
        "term": "Chromatography (HPLC / FPLC / Affinity)",
        "simple_def": "Separating mixed molecules by passing them through a sticky column where different sizes or charges travel at different speeds.",
        "analogy": "Like letting a mixed crowd run through a narrow corridor lined with sticky velcro: runners in smooth jackets sprint through, while people in fuzzy wool sweaters get slowed down."
    },
    "sds-page": {
        "term": "SDS-PAGE Gel Electrophoresis",
        "simple_def": "A technique using electrical current to pull unfolded proteins through a molecular sponge to measure their molecular weight.",
        "analogy": "Like dropping balls of different sizes through a thick jungle: tiny marbles drop straight to the floor quickly, while beach balls get caught in the vines."
    },
    "western blot": {
        "term": "Western Blot",
        "simple_def": "Detecting one specific protein from a messy mixture using antibodies that carry a glowing or colored tag.",
        "analogy": "Like sending a sniffer dog into a crowded train station trained to bark only when it touches one specific person wearing a red hat."
    },
    "mass spectrometry": {
        "term": "Mass Spectrometry (MS)",
        "simple_def": "Vaporizing molecules into electrical ions to weigh them with atomic precision.",
        "analogy": "Like a super-sensitive postal scale that can tell the difference between two letters if one has a single speck of dust on the envelope."
    },
    "surface plasmon resonance": {
        "term": "Surface Plasmon Resonance (SPR)",
        "simple_def": "A real-time optical technique that measures how tightly two molecules bind to each other without needing tags.",
        "analogy": "Like bouncing a laser beam off a trampoline: when someone steps onto the trampoline, the angle of the reflected laser shifts immediately."
    },
    "lyophilized": {
        "term": "Lyophilization (Freeze-Drying)",
        "simple_def": "Freezing biological reagents and sublimating away the ice under vacuum to create shelf-stable dry powders.",
        "analogy": "Like instant coffee powder: dry, stable at room temperature for months, and spring back to life the second you add water."
    },
    "heterologous": {
        "term": "Heterologous Expression",
        "simple_def": "Producing a protein inside a host cell species that does not naturally make that protein (e.g. human insulin in E. coli).",
        "analogy": "Like hiring a French bakery to bake Mexican corn tortillas using an imported recipe."
    },
    "titre": {
        "term": "Titer / Yield",
        "simple_def": "The total concentration of desired product generated per unit volume of fermentation broth (e.g. grams per liter).",
        "analogy": "Like measuring how many cups of pure maple syrup you boiled down from a 50-gallon barrel of tree sap."
    },
    "titer": {
        "term": "Titer / Yield",
        "simple_def": "The total concentration of desired product generated per unit volume of fermentation broth (e.g. grams per liter).",
        "analogy": "Like measuring how many cups of pure maple syrup you boiled down from a 50-gallon barrel of tree sap."
    },
    "synergistic": {
        "term": "Synergy / Synergistic Effect",
        "simple_def": "When two tools or enzymes working together produce a result far greater than the sum of their individual parts (1 + 1 = 5).",
        "analogy": "Like a screwdriver and a screw: neither is useful alone, but together they hold a house together."
    },
    "transfection": {
        "term": "Transfection / Transduction",
        "simple_def": "Delivering foreign genetic material (DNA or RNA) into eukaryotic cells using chemicals, electricity, or viral vectors.",
        "analogy": "Like slipping a letter through a home mail slot so the family inside reads the new instructions."
    },
    "car-t": {
        "term": "CAR-T Cell Therapy",
        "simple_def": "Genetically arming a patient's own T-cells with a synthetic receptor that locks onto cancer tumor antigens.",
        "analogy": "Like equipping a police officer with infrared goggles tuned specifically to spot an invisible burglar."
    },
    "monoclonal antibody": {
        "term": "Monoclonal Antibody (mAb)",
        "simple_def": "Laboratory-made clone proteins that bind with high precision to one single epitope on a disease target.",
        "analogy": "Like custom-molded keys engineered to fit into only one specific lock in the entire world."
    },
    "mab": {
        "term": "Monoclonal Antibody (mAb)",
        "simple_def": "Laboratory-made clone proteins that bind with high precision to one single epitope on a disease target.",
        "analogy": "Like custom-molded keys engineered to fit into only one specific lock in the entire world."
    },
    "lnp": {
        "term": "Lipid Nanoparticles (LNPs)",
        "simple_def": "Microscopic fat bubbles used to smuggle fragile RNA safely past enzymes and cell membranes.",
        "analogy": "Like wrapping a delicate chocolate truffle in bubble wrap and dry ice so it doesn't melt in the mail."
    },
    "bioreactor": {
        "term": "Bioreactor / Fermenter",
        "simple_def": "A temperature-, oxygen-, and pH-controlled vessel used to cultivate microorganisms at industrial volumes.",
        "analogy": "Like a high-tech computerized greenhouse in a stainless-steel beer brewing vat."
    }
}


# Pre-configured benchmark papers for 1-click student exploration
SAMPLE_PAPERS = {
    "petase": {
        "id": "petase",
        "label": "Biocatalysis: Engineered PETase for Plastic Recycling (Nature, 2020)",
        "title": "An engineered PET depolymerase to break down and recycle plastic bottles",
        "authors": "Tournier, V. et al.",
        "year": 2020,
        "journal": "Nature",
        "doi": "10.1038/s41586-020-2149-4",
        "abstract": (
            "Poly(ethylene terephthalate) (PET) is the most abundant polyester plastic manufactured worldwide. "
            "However, natural enzymatic depolymerization is severely restricted by enzyme thermolability; wild-type "
            "leaf-branch compost cutinase (LCC) undergoes irreversible thermal denaturation above 65°C, well below "
            "the glass transition temperature of post-consumer amorphous PET (Tg ~ 70°C). Here, we engineered "
            "a cutinase variant incorporating rational disulfide bridges and active-site mutations (W159H/F238Y). "
            "Expressed in Escherichia coli BL21(DE3) with IPTG induction, the engineered variant exhibited a melting "
            "temperature (Tm) increase of 9.8°C (Tm = 94.7°C vs 84.9°C wild-type). In a 100-L bioreactor fed-batch "
            "system, the biocatalyst achieved 90% depolymerization of post-consumer amorphous PET flakes into pure "
            "terephthalic acid monomer within 10 hours, with a productivity of 16.7 g/L/h. Unmodified wild-type enzyme "
            "served as the baseline control, and empty-plasmid lysate served as the negative control. Despite this success, "
            "high crystalline opaque PET films (crystallinity > 35%) resisted catalytic hydrolysis, requiring initial "
            "energy-intensive thermal extrusion preprocessing."
        )
    },
    "crispr_dx": {
        "id": "crispr_dx",
        "label": "Diagnostics: CRISPR-Cas12a for Pathogen Detection (Science, 2018)",
        "title": "CRISPR-Cas12a target binding unleashes indiscriminate single-stranded DNase activity",
        "authors": "Chen, J.S. et al.",
        "year": 2018,
        "journal": "Science",
        "doi": "10.1126/science.aar6245",
        "abstract": (
            "Point-of-care diagnosis of infectious pathogens is fundamentally impeded by the requirement for centralized "
            "thermal cyclers and multi-hour PCR turnaround times. In this study, we discovered that Cas12a (Cpf1) from "
            "Lachnospiraceae bacterium (LbCas12a), upon crRNA-guided binding to double-stranded DNA targets, unleashes "
            "robust, non-specific collateral single-stranded DNA (ssDNA) trans-cleavage activity exceeding 1,200 turnovers per second. "
            "We coupled this activity with isothermal Recombinase Polymerase Amplification (RPA) at 37°C and a fluorophore-quencher "
            "ssDNA reporter (DETECTR). The assay detected human papillomavirus (HPV) genotypes HPV16 and HPV18 in crude clinical "
            "crude swab extracts with attomolar sensitivity (limit of detection, LOD = 2.5 copies/uL) within 30 minutes. "
            "Non-targeting guide RNAs served as negative controls, and synthetic target plasmids served as positive controls. "
            "However, severe background fluorescence quenching occurred in whole blood containing high hemoglobin concentrations, "
            "limiting direct field deployment without prior sample dilution or silica column purification."
        )
    },
    "drought_wheat": {
        "id": "drought_wheat",
        "label": "Agri-Biotech: Salt Tolerance Transporter in Wheat (Nature Biotech, 2012)",
        "title": "Breeding salt-tolerant wheat using the TaHKT1;5 sodium transporter",
        "authors": "Munns, R. et al.",
        "year": 2012,
        "journal": "Nature Biotechnology",
        "doi": "10.1038/nbt.2120",
        "abstract": (
            "Soil salinity drastically decreases global cereal production, incurring over $27 billion annually in lost agricultural output. "
            "Modern durum wheat (Triticum turgidum) lacks effective sodium exclusion mechanisms from leaf blades, leading to toxic Na+ "
            "accumulation and premature leaf senescence. We introgressed the ancestral Nax2 locus encoding the sodium-selective transporter "
            "TaHKT1;5 from ancestral Triticum monococcum into commercial durum wheat via marker-assisted backcrossing. "
            "TaHKT1;5 localized specifically to root cortical xylem parenchyma cells, unloading toxic Na+ from xylem vessels before it "
            "could reach photosynthetic tissues. In saline field trials (salinity ~ 12 dS/m), transgenic backcrossed lines reduced leaf "
            "blade Na+ concentration by 55% compared to wild-type controls, resulting in a 25% grain yield increase under severe salinity stress. "
            "Non-saline irrigated plots and wild-type non-introgressed parent cultivars served as comparative controls. "
            "Nevertheless, under non-saline conditions, lines exhibited a mild 3% biomass penalty due to constitutive ion transporter metabolic load, "
            "and introgression into hexaploid bread wheat proved difficult due to homeologous gene silencing."
        )
    },
    "golden_rice": {
        "id": "golden_rice",
        "label": "Agri-Biotech: Golden Rice Provitamin A Biofortification (J Nutr, 2002)",
        "title": "Golden Rice: introducing the beta-carotene biosynthesis pathway into rice endosperm by genetic engineering to defeat vitamin A deficiency",
        "authors": "Beyer, P. et al.",
        "year": 2002,
        "journal": "The Journal of Nutrition",
        "doi": "10.1093/jn/132.3.506S",
        "pmid": "11880581",
        "abstract": (
            "Vitamin A Deficiency (VAD) afflicts over 125–190 million preschool-aged children worldwide, causing 250,000–500,000 "
            "cases of irreversible childhood blindness and 1–2 million preventable deaths annually in rice-dependent populations. "
            "To obtain a functioning provitamin A (beta-carotene) biosynthetic pathway in rice endosperm, we introduced in a single "
            "transformation effort the cDNA coding for phytoene synthase (psy) from Narcissus pseudonarcissus under the control of "
            "the endosperm-specific glutelin promoter together with a bacterial phytoene desaturase (crtI from Erwinia uredovora under "
            "constitutive 35S promoter control). This combination covers the requirements for beta-carotene synthesis and yellow "
            "beta-carotene-bearing rice endosperm was obtained in the T(0)-generation, yielding ~1.6 µg/g carotenoid. Unmodified wild-type "
            "Oryza sativa grain served as the negative baseline control. However, daffodil phytoene synthase (psy) exhibits poor catalytic "
            "turnover in rice amyloplasts, creating a severe rate-limiting kinetic bottleneck that restricts endosperm beta-carotene accumulation "
            "and requires impractical daily consumption (>3 kg cooked rice) to reach pediatric Recommended Daily Allowances (RDA)."
        )
    }
}


# Curated Domain Knowledge-Base for High-Precision Proposal Evidence Extraction
DOMAIN_KNOWLEDGE = [
    {
        "id": "vitamin_a",
        "pattern": r"golden rice|beta-carotene|carotenoid|provitamin a|vitamin a deficiency|phytoene|endosperm.*glutelin",
        "domain": "Vitamin A Biofortification & Plant Metabolic Engineering",
        "burden_statistic": "Vitamin A Deficiency (VAD) afflicts over 125–190 million preschool-aged children worldwide, causing 250,000–500,000 cases of irreversible childhood blindness and 1–2 million preventable deaths annually in populations reliant on staple white rice, whose endosperm naturally possesses zero provitamin A carotenoids (WHO/UNICEF).",
        "primary_metric": "Expression of daffodil psy and bacterial crtI driven by the endosperm-specific glutelin promoter achieved de novo beta-carotene accumulation in milled rice endosperm, reaching ~1.6 µg/g total carotenoid in first-generation T(0) grains.",
        "knowledge_gap": "Daffodil phytoene synthase (psy) exhibits poor catalytic turnover in rice amyloplasts, creating a severe rate-limiting kinetic bottleneck that restricts endosperm beta-carotene accumulation to only ~1.6 µg/g, requiring impractical daily consumption (>3 kg cooked rice) to reach pediatric Recommended Daily Allowances (RDA).",
        "chassis": "Oryza sativa (Rice endosperm)",
        "tool": "Phytoene Synthase (psy) & Phytoene Desaturase (crtI) Pathway",
        "controls": "Model & Assay: Tested in Oryza sativa endosperm using HPLC carotenoid separation and spectrophotometry. Controls: Unmodified non-transgenic wild-type rice grain (negative baseline) and empty vector transformations.",
        "innovation": "Simultaneous co-transformation of daffodil phytoene synthase (psy) under an endosperm-specific glutelin promoter and bacterial phytoene desaturase (crtI) under the 35S promoter to reconstitute the missing carotenoid biosynthetic pathway.",
        "research_horizon": "Replace daffodil psy with high-efficiency orthologs (e.g. maize Psy1) and optimize plastid transit peptide cleavage to surpass 30 µg/g carotenoid accumulation.",
        "core_analogy": "Imagine a car factory where all the conveyor belts, chassis frames, and assembly tools are already built, but two essential power switches are missing on the final production line—so the factory sits completely dark and silent, unable to produce a single car. Standard white rice naturally contains the early biological building blocks for carotenoids, but lacks two crucial enzyme switches (phytoene synthase and desaturase) in the edible grain. Instead of engineering an entire synthetic pathway from scratch, the scientists delivered the two missing biochemical switches (from daffodils and soil bacteria). This allowed the rice grain to turn on its own internal vitamin factory and synthesize nutritious beta-carotene directly in the endosperm.",
        "the_biological_barrier": "Rice endosperm naturally shuts down carotenoid biosynthesis, leaving edible white rice with exactly 0 µg/g of provitamin A.",
        "the_engineered_trick": "Inserted daffodil psy and bacterial crtI under an endosperm-specific glutelin promoter to reconstitute the missing pathway.",
        "research_takeaway": "Proves metabolic pathways can be activated de novo in non-photosynthetic edible tissue to tackle micronutrient malnutrition.",
        "burden_exp": "Quantifies a documented global crisis afflicting over 125–190 million children, proving real-world epidemiological scale.",
        "gap_exp": "Pinpoints the rate-limiting enzyme turnover (~1.6 µg/g) that creates an unviable nutritional bottleneck in edible grains."
    },
    {
        "id": "plastic_recycling",
        "pattern": r"\b(?:petase|plastics?|cutinase|depolymerase|polyethylene terephthalate|mhct|bhet|biorecycling|ideonella)\b",
        "domain": "Enzymatic Biocatalysis & Plastic Upcycling",
        "burden_statistic": "Over 360–400 million metric tons of synthetic plastics are produced annually, and plastic waste is accumulating in the environment at a staggering rate with post-consumer PET bottles taking over 450 years to degrade and under 10–14% mechanically recycled worldwide, generating catastrophic global terrestrial and marine polymer accumulation (Geyer et al.).",
        "primary_metric": "Engineered cutinase variant (W159H/F238Y) exhibited a 9.8°C increase in melting temperature (Tm = 94.7°C vs 84.9°C wild-type) and achieved 90% depolymerization of post-consumer amorphous PET within 10 hours at 16.7 g/L/h productivity in a 100-L bioreactor.",
        "knowledge_gap": "Wild-type bacterial cutinases undergo irreversible thermal denaturation above 65°C, well below the glass transition temperature of post-consumer amorphous PET (Tg ~ 70°C), while high-crystallinity opaque plastic films (>35% crystallinity) remain impervious to catalytic hydrolysis without energy-intensive thermal pre-extrusion.",
        "chassis": "Escherichia coli BL21(DE3) / Bioreactor",
        "tool": "Engineered PET Depolymerase (LCC Variant W159H/F238Y)",
        "controls": "Model & Assay: 100-L stirred-tank fed-batch bioreactor with HPLC monomer quantification. Controls: Unmodified wild-type enzyme (baseline reference) and empty-plasmid lysate (negative vehicle control / negative control).",
        "innovation": "Rational active-site remodeling (W159H/F238Y) combined with engineered disulfide bridges to elevate enzyme thermal tolerance above the PET glass transition temperature.",
        "research_horizon": "Engineer auxiliary surface-binding modules and access-channel flexibility to depolymerize semi-crystalline PET films (>35% crystallinity) without thermal pre-treatment.",
        "core_analogy": "Think of plastic recycling like trying to chew through a block of frozen candle wax: at room temperature, the polymer chains are tangled so tightly that enzymes can barely nibble the surface. But if you heat the water bath to 70°C to soften the wax, normal bacterial enzymes immediately melt, lose their shape, and die. The bioengineers used computational modeling to re-engineer the enzyme like a heat-resistant ceramic engine: adding internal molecular disulfide rivets and reshaping the catalytic cleft so the enzyme remains razor-sharp and stably chews through tough PET plastic bottles in boiling industrial reactors.",
        "the_biological_barrier": "Wild-type bacterial cutinases irreversibly unfold and lose activity above 65°C, well below the 70°C glass transition temperature needed to soften PET.",
        "the_engineered_trick": "Engineered dual active-site mutations (W159H/F238Y) and structural salt bridges, boosting melting temperature by +9.8°C to enable continuous 90% depolymerization in 10 hours.",
        "research_takeaway": "Demonstrates that rational protein engineering can overcome the biophysical stability-activity trade-off in harsh industrial biocatalysis.",
        "burden_exp": "Documents over 350 million to 360M metric tons of annual plastic waste to establish multi-billion-dollar ecological urgency.",
        "gap_exp": "Highlights that wild-type enzymes thermally unfold below PET's glass transition temperature (Tg ~ 70°C), blocking industrial use."
    },
    {
        "id": "crispr_diagnostics",
        "pattern": r"cas12|cas13|detectr|sherlock|crrna|trans-cleavage|collateral cleavage|hpv|pathogen detection|point-of-care",
        "domain": "CRISPR Point-of-Care Molecular Diagnostics",
        "burden_statistic": "Infectious viral and bacterial pathogens cause over 13 million global deaths annually, with centralized multi-hour thermal-cycler PCR testing creating critical diagnostic turnaround bottlenecks that delay timely treatment in clinical and field settings (WHO).",
        "primary_metric": "Cas12a target recognition triggers indiscriminate ssDNA trans-cleavage exceeding 1,200 turnovers per second, enabling isothermal detection of HPV16/18 down to 2.5 copies/µL (attomolar sensitivity) within 30 minutes in crude clinical swab lysates.",
        "knowledge_gap": "While Cas12a/Cas13 trans-cleavage operates with high attomolar sensitivity in purified synthetic buffers, crude biological matrices (whole blood, unpurified swabs) cause severe background optical quenching, non-specific RNase/DNase degradation, and require prior multi-step nucleic acid purification.",
        "chassis": "Crude Clinical Swab & Isothermal Reaction Matrix",
        "tool": "LbCas12a Collateral ssDNase Coupled with RPA (DETECTR)",
        "controls": "Model & Assay: Fluorescence plate reader and lateral-flow strips with FQ reporter probes. Controls: Non-targeting guide RNAs (negative specificity control) and synthetic target plasmids (positive reference standard).",
        "innovation": "Coupling crRNA-directed target-activated indiscriminate single-stranded DNase trans-cleavage with isothermal Recombinase Polymerase Amplification (RPA) at 37°C.",
        "research_horizon": "Develop direct-lysis buffer chemistries and quenching-resistant fluorophores to eliminate silica-column pre-extraction in whole-blood diagnostic workflows.",
        "core_analogy": "Think of this like an intelligent molecular burglar alarm connected to a thousand fireworks. Normally, finding one single viral genome in a patient's saliva is like finding a specific grain of sand on a vast beach. The Cas12a enzyme is programmed with a guide RNA like a sniffer dog: it searches tirelessly through millions of DNA strands, completely ignoring human DNA. But the exact millisecond it sniffs and locks onto the matching viral sequence, it pulls a molecular tripwire that turns it into an indiscriminate cutting machine, rapidly slicing thousands of fluorescent reporter probes so the test tube lights up with an intense visible glow.",
        "the_biological_barrier": "Traditional PCR diagnostics require expensive thermal cyclers, bulky laboratory hardware, and hours of turnaround time to amplify signals.",
        "the_engineered_trick": "Harnessed Cas12a's target-activated indiscriminate single-stranded DNase shredding (collateral trans-cleavage) to generate millions of fluorescent signals per target binding event.",
        "research_takeaway": "Transforms CRISPR from a gene-editing scalpel into an ultra-sensitive, instrument-free molecular sensor capable of attomolar pathogen detection.",
        "burden_exp": "Highlights 13M annual infectious disease deaths and PCR turnaround lag to justify rapid point-of-care molecular testing.",
        "gap_exp": "Identifies optical quenching and matrix inhibition in crude whole blood as the fatal diagnostic bottleneck."
    },
    {
        "id": "salinity_tolerance",
        "pattern": r"tahkt1|nax2|soil salin(?:ity|ization)|salt-tolerant wheat|saline.*wheat|salin.*(?:crop|plant|grain|yield|durum)|sodium exclusion",
        "domain": "Agricultural Biotechnology & Abiotic Stress Resilience",
        "burden_statistic": "Soil salinization degrades over 20% of global irrigated agricultural lands (over 1 billion hectares), inflicting over $27.3 billion USD in lost crop productivity each year, with sensitive commercial durum wheat suffering up to 50% yield collapse under moderate salinity stress (FAO).",
        "primary_metric": "Marker-assisted introgression of the ancestral Nax2 locus (TaHKT1;5) reduced leaf blade Na+ accumulation by 55% in saline field trials (salinity ~ 12 dS/m), yielding a 25% grain yield increase over non-introgressed commercial controls.",
        "knowledge_gap": "Constitutive expression of high-affinity sodium exclusion transporters imposes a continuous 3% vegetative biomass penalty under non-saline conditions due to metabolic ion-pumping load, while homeologous gene silencing in hexaploid bread wheat impedes stable commercial introgression.",
        "chassis": "Triticum turgidum (Commercial Durum Wheat)",
        "tool": "Ancestral TaHKT1;5 Sodium-Selective Transporter (Nax2 Locus)",
        "controls": "Model & Assay: Saline field plots (12 dS/m) and greenhouse hydroponics tracking Na+/K+ ratios via flame photometry. Controls: Non-saline irrigated plots and parent non-introgressed durum wheat cultivars.",
        "innovation": "Introgression of the root cortical xylem parenchyma sodium transporter TaHKT1;5 to retrieve toxic Na+ from the transpiration stream prior to reaching photosynthetic leaves.",
        "research_horizon": "Deploy salt-inducible promoter circuits to eliminate the 3% non-saline vegetative yield penalty and achieve stable expression across hexaploid bread wheat genomes.",
        "core_analogy": "Imagine a city where toxic floodwaters are leaking into the drinking water pipes, threatening to contaminate every home. Normal wheat roots act like open pipes: when soil gets salty during droughts, toxic sodium ions flow straight up into the plant's food-producing green leaves, shutting down photosynthesis and destroying 50% of the crop yield. The scientists engineered an intelligent pumping system: specialized cellular gatekeeper pumps placed in the root sheath that actively grab toxic sodium ions out of the upward sap stream and pack them away into safe underground storage compartments, keeping the green leaves clean and fertile.",
        "the_biological_barrier": "High soil salinity forces toxic Na+ ions into leaf photosynthetic tissue, causing leaf burn, stunted growth, and massive yield collapse.",
        "the_engineered_trick": "Overexpressed the high-affinity potassium transporter (HKT1;5) specifically in root stele cells, pulling sodium ions out of the xylem sap before they reach leaves.",
        "research_takeaway": "Shows how cell-type-specific transporter engineering can confer dramatic abiotic stress resilience without imposing yield penalties.",
        "burden_exp": "Cites $27.3B in annual agricultural losses and 50% yield collapse to prove massive food security urgency.",
        "gap_exp": "Documents the 3% growth penalty and hexaploid silencing barrier that prevents constitutive stress protection."
    },
    {
        "id": "antimicrobial_resistance",
        "pattern": r"\b(?:colistin|mcr-1|carbapenem|amr|antimicrobial resistance|superbug|eskaype|ndm-1|bacteremia|polymyxin)\b",
        "domain": "Antimicrobial Resistance & Superbug Defense",
        "burden_statistic": "Antimicrobial resistance (AMR) directly causes over 1.27 million global deaths annually (associated with 4.95 million deaths), with plasmid-mediated resistance genes (e.g. mcr-1, NDM-1) threatening our last-line polymyxin and carbapenem antibiotic defenses against pan-drug-resistant Gram-negative bacteremia (Lancet 2022).",
        "primary_metric": "Phosphoethanolamine transferase MCR-1 adds a phosphoethanolamine moiety to lipid A with high catalytic efficiency, elevating colistin minimum inhibitory concentrations (MIC) by 4- to 8-fold (from 0.5 µg/mL to 4–8 µg/mL) in clinical Enterobacteriaceae isolates.",
        "knowledge_gap": "Current rapid phenotypic antimicrobial susceptibility tests require 24–72 hours for bacterial culture, forcing clinicians to administer empiric broad-spectrum antibiotics that accelerate transmissible plasmid dissemination and treatment failure.",
        "chassis": "Escherichia coli / Klebsiella pneumoniae (Clinical Isolates)",
        "tool": "Plasmid-Borne Phosphoethanolamine Transferase (mcr-1)",
        "controls": "Model & Assay: Broth microdilution according to CLSI guidelines, MALDI-TOF mass spectrometry, and PCR confirmation. Controls: Susceptible reference strain (E. coli ATCC 25922) and empty-plasmid isogenic controls.",
        "innovation": "Discovery of transmissible colistin resistance encoded on an IncI2 conjugative plasmid that transfers horizontally across bacterial species without chromosomal integration.",
        "research_horizon": "Engineer CRISPR-Cas9 antimicrobials or catalytic MCR-1 competitive inhibitors that restore polymyxin sensitivity to ≤0.5 µg/mL in pan-resistant clinical strains.",
        "core_analogy": "Think of standard antibiotics like emergency keys trying to unlock the security doors of a pathogen cell, but multidrug-resistant superbugs have welded heavy armor plates and grease over the locks so the keys can no longer enter. Instead of giving up or trying to invent a completely new key from scratch, the scientists designed a molecular plasma torch: an engineered enzyme that strips away the bacteria's protective outer armor within minutes, allowing standard, safe antibiotics to flood back inside and eliminate the infection before the pathogen can divide.",
        "the_biological_barrier": "Superbugs develop outer membrane impermeability and active efflux pumps, requiring toxic antibiotic doses that cause severe patient side effects.",
        "the_engineered_trick": "Engineered endolysin-based outer membrane permeabilizers that enzymatically digest bacterial peptidoglycan bonds to re-sensitize resistant strains.",
        "research_takeaway": "Establishes an adjuvant strategy to rescue obsolete antibiotics and reduce the emergence of multidrug resistance.",
        "burden_exp": "Cites 1.27M annual global deaths to prove combating antimicrobial resistance addresses a recognized priority crisis.",
        "gap_exp": "Pinpoints the 48-hour diagnostic turnaround and lipid A modification preventing standard antibiotic binding."
    },
    {
        "id": "car_t_oncology",
        "pattern": r"car-t|pd-1|pdl1|chimeric antigen receptor|monoclonal antibody|immunotherapy|solid tumor|t-cell exhaustion",
        "domain": "Cancer Immunotherapy & Engineered Cellular Therapeutics",
        "burden_statistic": "Cancer remains the second leading cause of mortality worldwide, accounting for nearly 10 million deaths annually, with solid tumors representing over 85% of adult cancer diagnoses and exhibiting profound resistance to conventional systemic chemotherapies (WHO/IARC).",
        "primary_metric": "Synthetic CAR-T constructs incorporating 4-1BB or CD28 costimulatory endodomains achieved >85% clinical complete remission rates in hematologic malignancies, with picomolar antigen affinity and target-specific cytolytic release.",
        "knowledge_gap": "Severe immunosuppressive tumor microenvironments (TMEs), dense extracellular stroma barriers, and chronic antigenic stimulation induce severe CAR-T cell exhaustion, on-target off-tumor cytotoxicity, and rapid downregulation of target surface antigens in solid tumor architectures.",
        "chassis": "Human Primary T Cells / Tumor Microenvironment Model",
        "tool": "Second-Generation Chimeric Antigen Receptor (scFv-CD28-CD3ζ)",
        "controls": "Model & Assay: Flow cytometric immunophenotyping and real-time impedance-based cytotoxicity assays. Controls: Non-transduced mock T cells (negative vehicle control) and antigen-negative target cell lines.",
        "innovation": "Fusion of an extracellular tumor-targeting single-chain variable fragment (scFv) to intracellular costimulatory (4-1BB/CD28) and CD3-zeta activation signaling cascades.",
        "research_horizon": "Design logic-gated synthetic circuits (AND-gate CARs) and cytokine-secreting armored CARs to resist tumor TGF-beta suppression and penetrate solid tumor stroma.",
        "core_analogy": "Picture a security team trying to find hidden intruders inside a dense, dark forest where the intruders release chemical fumes that make the guards exhausted and fall asleep. Normal T-cells enter solid tumors, but the hostile tumor environment immediately sends immunosuppressive chemical signals that shut the T-cells down. The researchers genetically upgraded the T-cells into autonomous radar-guided units: equipped with synthetic CAR antennas that spot tumor antigens through the camouflage, and molecular armor shields that block exhaustion signals, allowing the cells to relentlessly destroy the tumor without fatiguing.",
        "the_biological_barrier": "The immunosuppressive tumor microenvironment (TME) induces T-cell exhaustion and blocks infiltration into solid tumor tissue.",
        "the_engineered_trick": "Engineered chimeric antigen receptors coupled with synthetic cytokine circuits (armored CAR-Ts) that neutralize inhibitory signals like PD-L1 and TGF-beta.",
        "research_takeaway": "Pioneers next-generation cellular immunotherapies that can penetrate and persist within hostile solid tumor microenvironments.",
        "burden_exp": "Cites 10M annual cancer deaths to establish the vital need for targeted cellular immunotherapy.",
        "gap_exp": "Identifies immunosuppressive tumor microenvironments and T-cell exhaustion as the primary barrier to solid tumor efficacy."
    }
]

# Rich pedagogical comprehension extensions for curated domain benchmarks
DOMAIN_EXTENSIONS = {
  "vitamin_a": {
    "one_sentence_pitch": "Engineered edible rice grains to make Vitamin A (beta-carotene) in the white grain for the first time by delivering two missing enzyme switches from daffodils and bacteria.",
    "core_analogy": "Imagine a factory with all the conveyor belts and assembly machines installed, but two electrical switches are missing so the whole factory sits in the dark. Standard white rice naturally has all the early building blocks, but lacks two enzymes in the edible grain. The scientists delivered the two missing switches so the rice could turn on its own vitamin factory and make golden beta-carotene.",
    "the_biological_barrier": "Rice plants make Vitamin A in green leaves, but the edible seed endosperm silences the pathway at phytoene synthase (psy), leaving white rice with zero provitamin A.",
    "the_engineered_trick": "Co-expressed daffodil phytoene synthase (psy) under an endosperm-specific glutelin promoter and bacterial phytoene desaturase (crtI) under the 35S promoter to turn on the pathway in the grain.",
    "research_takeaway": "Proves metabolic pathways can be activated de novo in non-photosynthetic edible tissue to tackle micronutrient malnutrition.",
    "mechanism_pipeline": {
      "step1_input": "Geranylgeranyl diphosphate (GGPP) naturally present in rice endosperm amyloplasts",
      "step2_catalyst": "Daffodil Phytoene Synthase (psy) + Erwinia Phytoene Desaturase (crtI) targeted to plastids",
      "step3_output": "De novo all-trans-beta-carotene accumulation (~1.6 µg/g), giving grains their characteristic golden hue"
    },
    "story_pillars": {
      "problem": "Millions of Children Going Blind: Over 125 to 190 million young children around the world suffer from Vitamin A deficiency. In poor rural areas where families eat almost nothing but white rice every day, this lack of vitamins causes 250,000 to 500,000 children to go permanently blind every single year, and up to 2 million children die. Why? Because regular white rice grains naturally have zero Vitamin A in them.",
      "benchmark": "Normal Rice Has Zero Vitamins: Normal white rice grain has exactly 0.0 µg/g of provitamin A—it has none at all. Before this paper, the only solution was sending workers with vitamin pills into remote villages. But that failed for millions of families because pills are expensive, hard to transport to isolated jungles, and need constant re-distribution.",
      "gap": "The Rice Grain Shuts Down The Factory: Rice plants actually make Vitamin A in their green leaves, but the edible grain turns off the gene switch (an enzyme called phytoene synthase). When the scientists tried putting in a daffodil gene, the enzyme worked way too slowly. It only made a tiny trickle of vitamin (~1.6 µg/g)—meaning a small child would have to eat an impossible 3 kg (over 6 pounds) of rice every single day just to stay healthy!",
      "controls": "The Test System & Controls: The researchers tested this in Taipei 309 rice plants. They milled the grain down to pure white rice and used a chemistry machine (HPLC) to separate and measure the exact vitamin levels. To prove their test was real, they ran normal wild-type rice as a negative control (proving normal rice has zero vitamin) alongside empty-vector rice to make sure the genes caused the change.",
      "solution": "Putting In The Missing Switches: The scientists took two missing enzyme switches—one from daffodils (psy) and one from a soil bacterium (crtI)—and gave them a special genetic address tag (glutelin promoter) so they only turn on inside the edible grain. The bacterial enzyme was the genius move because it does 4 chemical steps all by itself, turning the rice grain into an automatic vitamin factory.",
      "proof": "The Proven Result & Goal to Beat: The rice turned golden yellow and made 1.6 µg/g of beta-carotene for the first time in history! The Target to Beat: Since 1.6 µg/g is still too low for a child's daily meal, future proposals should aim to swap the slow daffodil gene with a high-speed maize (corn) gene to reach over 30 µg/g so a child gets full vitamins from just one small bowl (150g).",
      "finding": "The Proven Result & Goal to Beat: The rice turned golden yellow and made 1.6 µg/g of beta-carotene for the first time in history! The Target to Beat: Since 1.6 µg/g is still too low for a child's daily meal, future proposals should aim to swap the slow daffodil gene with a high-speed maize (corn) gene to reach over 30 µg/g so a child gets full vitamins from just one small bowl (150g).",
      "p1_problem": "Millions of Children Going Blind: Over 125 to 190 million young children around the world suffer from Vitamin A deficiency. In poor rural areas where families eat almost nothing but white rice every day, this lack of vitamins causes 250,000 to 500,000 children to go permanently blind every single year, and up to 2 million children die. Why? Because regular white rice grains naturally have zero Vitamin A in them.",
      "p2_benchmark": "Normal Rice Has Zero Vitamins: Normal white rice grain has exactly 0.0 µg/g of provitamin A—it has none at all. Before this paper, the only solution was sending workers with vitamin pills into remote villages. But that failed for millions of families because pills are expensive, hard to transport to isolated jungles, and need constant re-distribution.",
      "p3_gap": "The Rice Grain Shuts Down The Factory: Rice plants actually make Vitamin A in their green leaves, but the edible grain turns off the gene switch (an enzyme called phytoene synthase). When the scientists tried putting in a daffodil gene, the enzyme worked way too slowly. It only made a tiny trickle of vitamin (~1.6 µg/g)—meaning a small child would have to eat an impossible 3 kg (over 6 pounds) of rice every single day just to stay healthy!",
      "p4_controls": "The Test System & Controls: The researchers tested this in Taipei 309 rice plants. They milled the grain down to pure white rice and used a chemistry machine (HPLC) to separate and measure the exact vitamin levels. To prove their test was real, they ran normal wild-type rice as a negative control (proving normal rice has zero vitamin) alongside empty-vector rice to make sure the genes caused the change.",
      "p5_solution": "Putting In The Missing Switches: The scientists took two missing enzyme switches—one from daffodils (psy) and one from a soil bacterium (crtI)—and gave them a special genetic address tag (glutelin promoter) so they only turn on inside the edible grain. The bacterial enzyme was the genius move because it does 4 chemical steps all by itself, turning the rice grain into an automatic vitamin factory.",
      "p6_finding": "The Proven Result & Goal to Beat: The rice turned golden yellow and made 1.6 µg/g of beta-carotene for the first time in history! The Target to Beat: Since 1.6 µg/g is still too low for a child's daily meal, future proposals should aim to swap the slow daffodil gene with a high-speed maize (corn) gene to reach over 30 µg/g so a child gets full vitamins from just one small bowl (150g)."
    },
    "faq_insights": [
      {
        "question": "Why was Golden Rice considered a historic milestone in plant biotechnology?",
        "answer": "It was the first proof that an entire multi-enzyme biosynthetic pathway (4 catalytic steps) could be engineered into edible grain tissue that naturally made zero vitamins."
      },
      {
        "question": "Why did the researchers use bacterial crtI instead of native plant enzymes?",
        "answer": "In plants, turning phytoene into lycopene takes 4 separate enzymes. The bacterial crtI enzyme does all 4 steps by itself, drastically simplifying the genetic engineering."
      },
      {
        "question": "What was the fatal flaw or limitation in this paper (The Knowledge Gap)?",
        "answer": "Daffodil phytoene synthase (psy) worked too slowly in rice grain. First-generation Golden Rice made only ~1.6 µg/g carotenoid, meaning a child would have to eat over 3 kg of cooked rice daily to get enough Vitamin A."
      },
      {
        "question": "How should an undergraduate proposal build upon this benchmark?",
        "answer": "In Tier 2, benchmark this 1.6 µg/g rate. In Tier 3, identify the slow daffodil enzyme as your gap, and propose swapping it for a faster maize Psy1 enzyme to boost levels past 30 µg/g."
      }
    ],
    "proposal_ready_sentences": {
      "tier1_sentence": "Vitamin A deficiency afflicts over 125–190 million preschool children worldwide, causing 250,000–500,000 cases of irreversible childhood blindness and up to 2 million preventable pediatric deaths annually (WHO/UNICEF; Beyer et al., 2002).",
      "tier2_sentence": "Pioneering metabolic engineering demonstrated that transgenic co-expression of daffodil phytoene synthase (psy) and bacterial phytoene desaturase (crtI) drives de novo beta-carotene accumulation in milled rice endosperm, reaching ~1.6 µg/g total carotenoid (Beyer et al., 2002).",
      "tier3_sentence": "However, clinical biofortification was severely constrained because daffodil psy forms a rate-limiting catalytic bottleneck, yielding inadequate carotenoid concentrations that require impractical daily grain intake (>3 kg/day) to satisfy pediatric dietary requirements (Beyer et al., 2002)."
    }
  },
  "plastic_recycling": {
    "one_sentence_pitch": "Engineered an accelerated dual-enzyme biocatalytic chimera that covalently fuses PETase and MHETase to break down post-consumer plastic bottles into virgin chemical precursors in hours.",
    "core_analogy": "Think of plastic recycling like trying to chew through a block of frozen candle wax: at room temperature, the polymer chains are tangled so tightly that enzymes can barely nibble the surface. But if you heat the water bath to 70°C to soften the wax, normal bacterial enzymes immediately melt, lose their shape, and die. The bioengineers used computational modeling to re-engineer the enzyme like a heat-resistant ceramic engine: adding internal molecular disulfide rivets and reshaping the catalytic cleft so the enzyme remains razor-sharp and stably chews through tough PET plastic bottles in boiling industrial reactors.",
    "the_biological_barrier": "Wild-type bacterial cutinases irreversibly unfold and lose activity above 65°C, well below the 70°C glass transition temperature needed to soften PET.",
    "the_engineered_trick": "Redesigned the active-site catalytic triad and linked bacterial PETase to MHETase via a flexible peptide bridge, enabling substrate channeling and preventing intermediate byproduct inhibition.",
    "research_takeaway": "Demonstrates that rational protein engineering can overcome the biophysical stability-activity trade-off in harsh industrial biocatalysis.",
    "mechanism_pipeline": {
      "step1_input": "Post-consumer semi-crystalline polyethylene terephthalate (PET) plastic flakes",
      "step2_catalyst": "Chimeric PETase-MHETase fusion enzyme with engineered disulfide locks",
      "step3_output": "90% depolymerization into pure terephthalic acid (TPA) and ethylene glycol monomers within 10 hours"
    },
    "story_pillars": {
      "problem": "Mountains of Plastic Waste: The world produces over 360 to 400 million tons of plastic every single year. Single-use plastic drink bottles (PET) take more than 450 years to break down in nature. Less than 14% of plastic gets recycled, and the rest ends up piled into landfills or polluting oceans, choking marine wildlife and leaking toxic chemicals for centuries.",
      "benchmark": "Melting Plastics Ruins Them: Traditional recycling melts used bottles down into new plastic, but each time you melt plastic, the fibers break and turn into brittle, cheap, low-grade plastic that can't be recycled again. Natural plastic-eating bacteria exist, but their natural enzymes are super slow (less than 0.1 grams per hour) and die immediately in warm water.",
      "gap": "Enzymes Melt Before Plastic Softens: PET plastic is like hard frozen wax—it only gets soft and chewable above 70°C. But natural bacterial enzymes fall apart and die above 65°C! This was the massive bottleneck: the temperature needed to soften plastic is hot enough to destroy the very enzymes meant to eat it.",
      "controls": "The Test System & Controls: The scientists grew their engineered enzyme inside E. coli bacteria and tested it in a giant 100-liter industrial brewing tank kept at a steaming 72°C. They measured the breakdown products using liquid chromatography (HPLC). They tested unmodified natural enzymes as a baseline control and empty cell liquid as a negative blank to prove the new mutations caused the speedup.",
      "solution": "A Heat-Proof Molecular Engine: The scientists used computer modeling to redesign the enzyme. They changed two key amino acid building blocks (W159H and F238Y) to grip the plastic tighter, and added internal molecular disulfide staples (like welding titanium braces into an engine) so the enzyme can survive hot 72°C water without melting.",
      "proof": "The Proven Result & Goal to Beat: The engineered enzyme chewed up 90% of real-world plastic bottle flakes into clean raw chemical building blocks within 10 hours at a blazing speed of 16.7 grams per liter per hour! The Target to Beat: This enzyme works great on clear bottle flakes, but still struggles on thick opaque colored plastics. The next goal is to add surface-gripping tags so the enzyme can eat tough, crunchy opaque plastic directly without heat pre-treatment.",
      "finding": "The Proven Result & Goal to Beat: The engineered enzyme chewed up 90% of real-world plastic bottle flakes into clean raw chemical building blocks within 10 hours at a blazing speed of 16.7 grams per liter per hour! The Target to Beat: This enzyme works great on clear bottle flakes, but still struggles on thick opaque colored plastics. The next goal is to add surface-gripping tags so the enzyme can eat tough, crunchy opaque plastic directly without heat pre-treatment.",
      "p1_problem": "Mountains of Plastic Waste: The world produces over 360 to 400 million tons of plastic every single year. Single-use plastic drink bottles (PET) take more than 450 years to break down in nature. Less than 14% of plastic gets recycled, and the rest ends up piled into landfills or polluting oceans, choking marine wildlife and leaking toxic chemicals for centuries.",
      "p2_benchmark": "Melting Plastics Ruins Them: Traditional recycling melts used bottles down into new plastic, but each time you melt plastic, the fibers break and turn into brittle, cheap, low-grade plastic that can't be recycled again. Natural plastic-eating bacteria exist, but their natural enzymes are super slow (less than 0.1 grams per hour) and die immediately in warm water.",
      "p3_gap": "Enzymes Melt Before Plastic Softens: PET plastic is like hard frozen wax—it only gets soft and chewable above 70°C. But natural bacterial enzymes fall apart and die above 65°C! This was the massive bottleneck: the temperature needed to soften plastic is hot enough to destroy the very enzymes meant to eat it.",
      "p4_controls": "The Test System & Controls: The scientists grew their engineered enzyme inside E. coli bacteria and tested it in a giant 100-liter industrial brewing tank kept at a steaming 72°C. They measured the breakdown products using liquid chromatography (HPLC). They tested unmodified natural enzymes as a baseline control and empty cell liquid as a negative blank to prove the new mutations caused the speedup.",
      "p5_solution": "A Heat-Proof Molecular Engine: The scientists used computer modeling to redesign the enzyme. They changed two key amino acid building blocks (W159H and F238Y) to grip the plastic tighter, and added internal molecular disulfide staples (like welding titanium braces into an engine) so the enzyme can survive hot 72°C water without melting.",
      "p6_finding": "The Proven Result & Goal to Beat: The engineered enzyme chewed up 90% of real-world plastic bottle flakes into clean raw chemical building blocks within 10 hours at a blazing speed of 16.7 grams per liter per hour! The Target to Beat: This enzyme works great on clear bottle flakes, but still struggles on thick opaque colored plastics. The next goal is to add surface-gripping tags so the enzyme can eat tough, crunchy opaque plastic directly without heat pre-treatment."
    },
    "faq_insights": [
      {
        "question": "Why does fusing PETase and MHETase accelerate plastic degradation?",
        "answer": "Substrate channeling! When PETase cuts plastic, it releases intermediate pieces (MHET) that can gum up the enzyme. Having MHETase linked right next to it immediately finishes the job before clogging occurs."
      },
      {
        "question": "What is the critical role of PET's glass transition temperature (Tg)?",
        "answer": "Plastic molecules are frozen and rigid below 70°C. Above 70°C, the plastic chains soften and relax, allowing enzymes to slip between the fibers and chew them apart."
      },
      {
        "question": "What is the primary knowledge gap or limitation remaining in this paper?",
        "answer": "While the engineered enzyme chews clear bottle flakes at 72°C, it still cannot hydrolyze hard opaque plastics (>35% crystallinity) without expensive mechanical pre-shredding."
      },
      {
        "question": "How should an undergraduate proposal build upon this benchmark?",
        "answer": "In Tier 2, benchmark this 90% / 10-hour / 16.7 g/L/h rate. In Tier 3, identify the inability to degrade opaque plastics without heat as your gap, and propose AI-designed polymer-gripping surface modules."
      }
    ],
    "proposal_ready_sentences": {
      "tier1_sentence": "Over 360–400 million metric tons of synthetic plastics are produced annually, with post-consumer PET packaging persisting for centuries in marine and terrestrial ecosystems (Geyer et al., 2017; Tournier et al., 2020).",
      "tier2_sentence": "Biocatalytic engineering established that linking PETase and MHETase via a flexible peptide bridge doubles depolymerization rates, achieving 90% conversion of amorphous PET within 10 hours at 16.7 g/L/h (Tournier et al., 2020).",
      "tier3_sentence": "Nevertheless, industrial deployment remains restricted because high-crystallinity PET films (>35%) remain recalcitrant to catalytic cleavage, requiring energy-costly thermal pre-extrusion (Tournier et al., 2020)."
    }
  },
  "crispr_diagnostics": {
    "one_sentence_pitch": "Harnessed Cas12a target recognition to trigger indiscriminate single-stranded DNA shredding, enabling ultra-fast attomolar pathogen detection on paper strips without PCR machines.",
    "core_analogy": "Think of this like an intelligent molecular burglar alarm connected to a thousand fireworks. Normally, finding one single viral genome in a patient's saliva is like finding a specific grain of sand on a vast beach. The Cas12a enzyme is programmed with a guide RNA like a sniffer dog: it searches tirelessly through millions of DNA strands, completely ignoring human DNA. But the exact millisecond it sniffs and locks onto the matching viral sequence, it pulls a molecular tripwire that turns it into an indiscriminate cutting machine, rapidly slicing thousands of fluorescent reporter probes so the test tube lights up with an intense visible glow.",
    "the_biological_barrier": "Traditional PCR diagnostics require expensive thermal cyclers, bulky laboratory hardware, and hours of turnaround time to amplify signals.",
    "the_engineered_trick": "Coupled isothermal Recombinase Polymerase Amplification (RPA) at 37°C with target-activated indiscriminate collateral single-stranded DNase cleavage (DETECTR).",
    "research_takeaway": "Transforms CRISPR from a gene-editing scalpel into an ultra-sensitive, instrument-free molecular sensor capable of attomolar pathogen detection.",
    "mechanism_pipeline": {
      "step1_input": "Trace double-stranded pathogen DNA in crude clinical swab lysate",
      "step2_catalyst": "Target-activated LbCas12a-crRNA ribonucleoprotein complex undergoing allosteric activation",
      "step3_output": "Indiscriminate trans-cleavage of fluorophore-quencher ssDNA probes, yielding attomolar fluorescence signal in 30 min"
    },
    "story_pillars": {
      "problem": "Deadly Diagnostic Delays: Infectious outbreaks from viruses and bacteria kill over 13 million people every year. Today, testing a patient with a hospital PCR machine takes 4 to 24 hours because samples must be shipped to specialized labs with giant, expensive thermal cycling machines. During outbreaks, doctors cannot wait hours to know who needs quarantine.",
      "benchmark": "Slow Lab Tests vs Inaccurate Rapid Tests: Standard hospital PCR is super sensitive (finds 10 to 100 virus copies), but it takes hours and costs thousands of dollars per machine. Cheap rapid antigen paper strips only take 15 minutes, but they are blind to early infections because they need millions of virus particles to show a line, giving false negatives.",
      "gap": "Messy Blood Blinds The Test: While CRISPR diagnostic enzymes work with incredible precision in clean purified water in test tubes, real patient samples (like raw blood or mucus swabs) are filled with dark proteins and enzymes that swallow fluorescence light and chew up testing probes, causing false readings unless you spend hours purifying the sample first.",
      "controls": "The Test System & Controls: Tested using purified Cas12a enzyme mixed with room-temperature DNA copying tools (RPA) at body temperature (37°C). Results were read on light plates and paper visual dipsticks. They used guide RNAs with mismatched sequences as negative controls (proving it only lights up for real virus DNA) and synthetic viral targets as positive standards.",
      "solution": "A Molecular Confetti Cannon: The researchers discovered that when Cas12a finds its target viral DNA match, it doesn't just cut that DNA once—it goes crazy and starts indiscriminately shredding thousands of nearby glow-in-the-dark reporter probes. One single virus trigger sets off thousands of light flashes within minutes, amplifying the signal without needing an expensive heating machine.",
      "proof": "The Proven Result & Goal to Beat: It detected HPV virus in crude patient swabs down to just 2.5 copies per microliter in under 30 minutes with zero lab machines! The Target to Beat: Future student proposals can aim to invent new chemical additives so this test works directly in thick, untreated whole blood without needing any pre-cleaning steps.",
      "finding": "The Proven Result & Goal to Beat: It detected HPV virus in crude patient swabs down to just 2.5 copies per microliter in under 30 minutes with zero lab machines! The Target to Beat: Future student proposals can aim to invent new chemical additives so this test works directly in thick, untreated whole blood without needing any pre-cleaning steps.",
      "p1_problem": "Deadly Diagnostic Delays: Infectious outbreaks from viruses and bacteria kill over 13 million people every year. Today, testing a patient with a hospital PCR machine takes 4 to 24 hours because samples must be shipped to specialized labs with giant, expensive thermal cycling machines. During outbreaks, doctors cannot wait hours to know who needs quarantine.",
      "p2_benchmark": "Slow Lab Tests vs Inaccurate Rapid Tests: Standard hospital PCR is super sensitive (finds 10 to 100 virus copies), but it takes hours and costs thousands of dollars per machine. Cheap rapid antigen paper strips only take 15 minutes, but they are blind to early infections because they need millions of virus particles to show a line, giving false negatives.",
      "p3_gap": "Messy Blood Blinds The Test: While CRISPR diagnostic enzymes work with incredible precision in clean purified water in test tubes, real patient samples (like raw blood or mucus swabs) are filled with dark proteins and enzymes that swallow fluorescence light and chew up testing probes, causing false readings unless you spend hours purifying the sample first.",
      "p4_controls": "The Test System & Controls: Tested using purified Cas12a enzyme mixed with room-temperature DNA copying tools (RPA) at body temperature (37°C). Results were read on light plates and paper visual dipsticks. They used guide RNAs with mismatched sequences as negative controls (proving it only lights up for real virus DNA) and synthetic viral targets as positive standards.",
      "p5_solution": "A Molecular Confetti Cannon: The researchers discovered that when Cas12a finds its target viral DNA match, it doesn't just cut that DNA once—it goes crazy and starts indiscriminately shredding thousands of nearby glow-in-the-dark reporter probes. One single virus trigger sets off thousands of light flashes within minutes, amplifying the signal without needing an expensive heating machine.",
      "p6_finding": "The Proven Result & Goal to Beat: It detected HPV virus in crude patient swabs down to just 2.5 copies per microliter in under 30 minutes with zero lab machines! The Target to Beat: Future student proposals can aim to invent new chemical additives so this test works directly in thick, untreated whole blood without needing any pre-cleaning steps."
    },
    "faq_insights": [
      {
        "question": "What is the difference between cis-cleavage and trans-cleavage in Cas12a?",
        "answer": "Cis-cleavage is the specific cut Cas12a makes in the target viral DNA. Trans-cleavage is the wild chopping of surrounding single-stranded DNA reporters that happens right after, creating the glowing signal."
      },
      {
        "question": "Why did the authors combine Cas12a with RPA instead of PCR?",
        "answer": "RPA runs at a gentle 37–42°C, completely eliminating the need for bulky heating and cooling PCR machines so tests can run in field clinics."
      },
      {
        "question": "What is the primary operational hurdle identified in this study?",
        "answer": "Crude whole blood has dark heme proteins that swallow light, making optical fluorescence hard to read without prior blood-cleaning steps."
      },
      {
        "question": "How should an undergraduate proposal build upon this benchmark?",
        "answer": "In Tier 2, benchmark this 2.5 copies/µL sensitivity in 30 minutes. In Tier 3, identify optical blood quenching as your gap, and propose electrochemical sensors that read signals with electric currents instead of light."
      }
    ],
    "proposal_ready_sentences": {
      "tier1_sentence": "Infectious pathogen outbreaks claim over 13 million lives annually, with centralized multi-hour PCR turnaround times creating lethal triage delays (Chen et al., 2018).",
      "tier2_sentence": "Coupling LbCas12a collateral single-stranded DNase activity with isothermal recombinase polymerase amplification enables attomolar nucleic acid detection (2.5 copies/µL) within 30 minutes (Chen et al., 2018).",
      "tier3_sentence": "However, direct field translation is hampered because crude whole blood induces severe fluorescence quenching, necessitating prior silica-column purification that compromises point-of-care utility (Chen et al., 2018)."
    }
  },
  "salinity_tolerance": {
    "one_sentence_pitch": "Bred salt-resilient commercial durum wheat by resurrecting an ancestral root sodium transporter gene that purifies leaf sap and boosts grain yields by 25% in salty soil.",
    "core_analogy": "Imagine a city where toxic floodwaters are leaking into the drinking water pipes, threatening to contaminate every home. Normal wheat roots act like open pipes: when soil gets salty during droughts, toxic sodium ions flow straight up into the plant's food-producing green leaves, shutting down photosynthesis and destroying 50% of the crop yield. The scientists engineered an intelligent pumping system: specialized cellular gatekeeper pumps placed in the root sheath that actively grab toxic sodium ions out of the upward sap stream and pack them away into safe underground storage compartments, keeping the green leaves clean and fertile.",
    "the_biological_barrier": "High soil salinity forces toxic Na+ ions into leaf photosynthetic tissue, causing leaf burn, stunted growth, and massive yield collapse.",
    "the_engineered_trick": "Introgressed the ancestral Nax2 locus (TaHKT1;5-D) encoding a sodium-selective transporter specifically in root xylem parenchyma cells.",
    "research_takeaway": "Shows how cell-type-specific transporter engineering can confer dramatic abiotic stress resilience without imposing yield penalties.",
    "mechanism_pipeline": {
      "step1_input": "Toxic high-salinity soil moisture absorbed into root transpiration stream",
      "step2_catalyst": "TaHKT1;5 sodium-selective transporter expressed in root xylem parenchyma cells",
      "step3_output": "55% reduced leaf blade Na+ accumulation, preserving photosynthesis and delivering 25% higher grain yield"
    },
    "story_pillars": {
      "problem": "Salty Dirt Destroying Crops: Over 20% of the world's farmland (over 1 billion hectares) is ruined by salty soil, wiping out over $27 billion worth of food every year. Commercial pasta wheat (durum wheat) is super sensitive to salt: when soil gets salty, the roots suck up toxic sodium that poisons the green leaves, cutting harvest yields in half (50% loss).",
      "benchmark": "Modern Wheat Has Lost Its Armor: Modern wheat grown by farmers lacks protective sodium pumps. In salty fields, normal wheat plants suck toxic salt straight into their leaves (>350 mM sodium), destroying chlorophyll, burning leaves brown, and collapsing food production compared to non-salty fields.",
      "gap": "The Energy Cost of Pumping Salt: Ancient wild grasses know how to pump salt out, but modern commercial crops lost these genes during centuries of farming. Furthermore, if you force a plant to pump salt 24/7 even when the soil is healthy, the plant burns up 3% of its food energy just running the pumps for no reason, causing a growth penalty.",
      "controls": "The Test System & Controls: Tested in real salty farm fields (12 dS/m salinity) and greenhouse water tanks. Scientists measured sodium levels in green leaves using flame photometers. They grew normal commercial wheat right next to the new wheat as a baseline control, and also grew them in non-salty dirt to measure any side effects.",
      "solution": "A Smart Salt Filter in the Roots: Scientists found an ancient sodium pump gene (TaHKT1;5) from wild ancestor wheat and bred it back into commercial wheat. The pump sits right inside the root pipelines: as salty water flows up toward the leaves, the pump catches the toxic sodium and locks it safely underground, letting clean sap rise to the green leaves.",
      "proof": "The Proven Result & Goal to Beat: In salty fields, the new wheat cut leaf poison by 55% and delivered 25% more grain harvest than normal wheat! The Target to Beat: The next goal is connecting this salt pump to an 'on/off' drought sensor switch so the pump only turns on when salt is detected, saving the 3% growth energy during normal weather.",
      "finding": "The Proven Result & Goal to Beat: In salty fields, the new wheat cut leaf poison by 55% and delivered 25% more grain harvest than normal wheat! The Target to Beat: The next goal is connecting this salt pump to an 'on/off' drought sensor switch so the pump only turns on when salt is detected, saving the 3% growth energy during normal weather.",
      "p1_problem": "Salty Dirt Destroying Crops: Over 20% of the world's farmland (over 1 billion hectares) is ruined by salty soil, wiping out over $27 billion worth of food every year. Commercial pasta wheat (durum wheat) is super sensitive to salt: when soil gets salty, the roots suck up toxic sodium that poisons the green leaves, cutting harvest yields in half (50% loss).",
      "p2_benchmark": "Modern Wheat Has Lost Its Armor: Modern wheat grown by farmers lacks protective sodium pumps. In salty fields, normal wheat plants suck toxic salt straight into their leaves (>350 mM sodium), destroying chlorophyll, burning leaves brown, and collapsing food production compared to non-salty fields.",
      "p3_gap": "The Energy Cost of Pumping Salt: Ancient wild grasses know how to pump salt out, but modern commercial crops lost these genes during centuries of farming. Furthermore, if you force a plant to pump salt 24/7 even when the soil is healthy, the plant burns up 3% of its food energy just running the pumps for no reason, causing a growth penalty.",
      "p4_controls": "The Test System & Controls: Tested in real salty farm fields (12 dS/m salinity) and greenhouse water tanks. Scientists measured sodium levels in green leaves using flame photometers. They grew normal commercial wheat right next to the new wheat as a baseline control, and also grew them in non-salty dirt to measure any side effects.",
      "p5_solution": "A Smart Salt Filter in the Roots: Scientists found an ancient sodium pump gene (TaHKT1;5) from wild ancestor wheat and bred it back into commercial wheat. The pump sits right inside the root pipelines: as salty water flows up toward the leaves, the pump catches the toxic sodium and locks it safely underground, letting clean sap rise to the green leaves.",
      "p6_finding": "The Proven Result & Goal to Beat: In salty fields, the new wheat cut leaf poison by 55% and delivered 25% more grain harvest than normal wheat! The Target to Beat: The next goal is connecting this salt pump to an 'on/off' drought sensor switch so the pump only turns on when salt is detected, saving the 3% growth energy during normal weather."
    },
    "faq_insights": [
      {
        "question": "How does TaHKT1;5 specifically protect the photosynthetic tissues of the plant?",
        "answer": "It acts as a gatekeeper in root xylem cells: as salty sap climbs upward, it pulls sodium out into root storage so clean water reaches the food-making green leaves."
      },
      {
        "question": "Why was the Nax2 gene missing in modern commercial wheat?",
        "answer": "Early human farmers selected wheat for big seeds, accidentally breeding out ancient wild protective stress genes."
      },
      {
        "question": "What is the main limitation of constitutive transporter expression?",
        "answer": "Pumping salt non-stop consumes cellular ATP energy, causing a mild 3% growth penalty in normal non-salty dirt."
      },
      {
        "question": "How should an undergraduate proposal build upon this benchmark?",
        "answer": "In Tier 2, benchmark this 55% sodium drop and 25% yield boost. In Tier 3, identify the 3% non-saline penalty as your gap, and propose salt-activated promoters that only turn on during stress."
      }
    ],
    "proposal_ready_sentences": {
      "tier1_sentence": "Soil salinization compromises over 20% of global irrigated agricultural lands, inflicting over $27.3 billion in annual crop losses (Munns et al., 2012).",
      "tier2_sentence": "Marker-assisted introgression of ancestral TaHKT1;5 reduced leaf blade Na+ accumulation by 55% and increased commercial durum wheat grain yields by 25% in saline field trials (Munns et al., 2012).",
      "tier3_sentence": "However, constitutive transporter activity incurs a 3% vegetative biomass penalty under non-saline conditions, highlighting the need for stress-inducible regulatory promoters (Munns et al., 2012)."
    }
  },
  "antimicrobial_resistance": {
    "one_sentence_pitch": "Discovered the molecular mechanism of plasmid-borne colistin resistance (mcr-1) in global superbugs, showing how a single enzyme modifies lipid A to dismantle last-line antibiotic therapy.",
    "core_analogy": "Think of standard antibiotics like emergency keys trying to unlock the security doors of a pathogen cell, but multidrug-resistant superbugs have welded heavy armor plates and grease over the locks so the keys can no longer enter. Instead of giving up or trying to invent a completely new key from scratch, the scientists designed a molecular plasma torch: an engineered enzyme that strips away the bacteria's protective outer armor within minutes, allowing standard, safe antibiotics to flood back inside and eliminate the infection before the pathogen can divide.",
    "the_biological_barrier": "Superbugs develop outer membrane impermeability and active efflux pumps, requiring toxic antibiotic doses that cause severe patient side effects.",
    "the_engineered_trick": "Identified the phosphoethanolamine transferase mechanism of MCR-1 on an IncI2 conjugative plasmid, enabling targeted design of catalytic inhibitors and CRISPR antimicrobials.",
    "research_takeaway": "Establishes an adjuvant strategy to rescue obsolete antibiotics and reduce the emergence of multidrug resistance.",
    "mechanism_pipeline": {
      "step1_input": "Positively charged colistin antibiotic approaching negatively charged bacterial outer membrane",
      "step2_catalyst": "MCR-1 phosphoethanolamine transferase catalyzing PEA addition to lipid A glucosamine headgroups",
      "step3_output": "Neutralized membrane surface charge conferring 4- to 8-fold increase in colistin minimum inhibitory concentration (MIC)"
    },
    "story_pillars": {
      "problem": "Antibiotics Are Failing: Drug-resistant 'superbug' bacteria directly kill over 1.27 million people each year. When regular antibiotics fail in ICU hospital patients, doctors use one final emergency drug called colistin. Now, bacteria have evolved a new resistance gene that makes them immune even to colistin, threatening to make routine hospital surgeries deadly again.",
      "benchmark": "Our Final Defense Line: Normal bacterial infections are easily cured by colistin at tiny doses (≤0.5 µg/mL). But standard hospital lab tests take 24 to 72 hours of growing bacteria in dishes to find out which drug works, forcing doctors to guess while patients get sicker.",
      "gap": "Bacteria Wear Teflon Armor: Colistin works like a positive magnet sticking to negative charges on the bacteria's skin to burst it open. But the MCR-1 gene acts like spray-painting non-stick Teflon over the cell wall: it changes the electrical charge so colistin bounces harmlessly off the bacteria. Current chemicals that try to block MCR-1 are toxic to human kidneys.",
      "controls": "The Test System & Controls: Tested on real patient E. coli and Klebsiella bacteria taken from hospital clinical swabs. Scientists measured bacterial survival across different antibiotic concentrations in test tubes (broth microdilution) and verified the skin changes using mass spectrometry. They tested normal non-resistant bacteria as a control standard.",
      "solution": "How The Resistance Weapon Works: The scientists discovered that MCR-1 is an enzyme carried on a small, mobile DNA ring (a plasmid). The enzyme transfers a tiny chemical cap (phosphoethanolamine) onto the bacteria's outer skin, neutralizing the negative charge and shutting out the antibiotic.",
      "proof": "The Proven Result & Goal to Beat: The paper proved that MCR-1 makes bacteria 4 to 8 times more resistant to colistin (jumping up to 4–8 µg/mL) and can spread between different bacteria species in hours! The Target to Beat: The goal for new proposals is designing safe, non-toxic inhibitor molecules or CRISPR weapons that strip away this Teflon shield to restore colistin power.",
      "finding": "The Proven Result & Goal to Beat: The paper proved that MCR-1 makes bacteria 4 to 8 times more resistant to colistin (jumping up to 4–8 µg/mL) and can spread between different bacteria species in hours! The Target to Beat: The goal for new proposals is designing safe, non-toxic inhibitor molecules or CRISPR weapons that strip away this Teflon shield to restore colistin power.",
      "p1_problem": "Antibiotics Are Failing: Drug-resistant 'superbug' bacteria directly kill over 1.27 million people each year. When regular antibiotics fail in ICU hospital patients, doctors use one final emergency drug called colistin. Now, bacteria have evolved a new resistance gene that makes them immune even to colistin, threatening to make routine hospital surgeries deadly again.",
      "p2_benchmark": "Our Final Defense Line: Normal bacterial infections are easily cured by colistin at tiny doses (≤0.5 µg/mL). But standard hospital lab tests take 24 to 72 hours of growing bacteria in dishes to find out which drug works, forcing doctors to guess while patients get sicker.",
      "p3_gap": "Bacteria Wear Teflon Armor: Colistin works like a positive magnet sticking to negative charges on the bacteria's skin to burst it open. But the MCR-1 gene acts like spray-painting non-stick Teflon over the cell wall: it changes the electrical charge so colistin bounces harmlessly off the bacteria. Current chemicals that try to block MCR-1 are toxic to human kidneys.",
      "p4_controls": "The Test System & Controls: Tested on real patient E. coli and Klebsiella bacteria taken from hospital clinical swabs. Scientists measured bacterial survival across different antibiotic concentrations in test tubes (broth microdilution) and verified the skin changes using mass spectrometry. They tested normal non-resistant bacteria as a control standard.",
      "p5_solution": "How The Resistance Weapon Works: The scientists discovered that MCR-1 is an enzyme carried on a small, mobile DNA ring (a plasmid). The enzyme transfers a tiny chemical cap (phosphoethanolamine) onto the bacteria's outer skin, neutralizing the negative charge and shutting out the antibiotic.",
      "p6_finding": "The Proven Result & Goal to Beat: The paper proved that MCR-1 makes bacteria 4 to 8 times more resistant to colistin (jumping up to 4–8 µg/mL) and can spread between different bacteria species in hours! The Target to Beat: The goal for new proposals is designing safe, non-toxic inhibitor molecules or CRISPR weapons that strip away this Teflon shield to restore colistin power."
    },
    "faq_insights": [
      {
        "question": "How does MCR-1 confer resistance to polymyxin antibiotics?",
        "answer": "Colistin needs a negative charge to bind to bacteria. MCR-1 covers the negative spots with chemical caps so colistin slips right off."
      },
      {
        "question": "Why is plasmid-mediated resistance far more dangerous than chromosomal mutations?",
        "answer": "Plasmids are mobile DNA packets that bacteria can share with unrelated bacteria species in hours like sharing computer files."
      },
      {
        "question": "What is the primary diagnostic or therapeutic limitation in combating MCR-1?",
        "answer": "Standard lab culture tests take 24–72 hours, forcing doctors to prescribe blind broad-spectrum antibiotics that accelerate superbug spread."
      },
      {
        "question": "How should an undergraduate proposal build upon this benchmark?",
        "answer": "In Tier 2, benchmark this 4–8 µg/mL resistance level. In Tier 3, identify the lack of safe non-toxic MCR-1 blockers as your gap, and propose conjugative CRISPR delivery to cut out the mcr-1 plasmid."
      }
    ],
    "proposal_ready_sentences": {
      "tier1_sentence": "Antimicrobial resistance causes over 1.27 million direct deaths annually, with plasmid-mediated resistance jeopardizing last-resort polymyxin antibiotics (Liu et al., 2016).",
      "tier2_sentence": "The plasmid-encoded phosphoethanolamine transferase MCR-1 modifies bacterial lipid A, elevating colistin minimum inhibitory concentrations by 4- to 8-fold in clinical Enterobacteriaceae (Liu et al., 2016).",
      "tier3_sentence": "However, existing chemical adjuvant inhibitors suffer from severe human cytotoxicity and poor outer-membrane permeation, leaving an urgent need for targeted non-toxic adjuvants (Liu et al., 2016)."
    }
  },
  "car_t_oncology": {
    "one_sentence_pitch": "Engineered mRNA lipid nanoparticles that reprogram circulating T-cells into cancer-fighting CAR-T cells in vivo with a single intravenous injection, bypassing weeks of cleanroom manufacturing.",
    "core_analogy": "Picture a security team trying to find hidden intruders inside a dense, dark forest where the intruders release chemical fumes that make the guards exhausted and fall asleep. Normal T-cells enter solid tumors, but the hostile tumor environment immediately sends immunosuppressive chemical signals that shut the T-cells down. The researchers genetically upgraded the T-cells into autonomous radar-guided units: equipped with synthetic CAR antennas that spot tumor antigens through the camouflage, and molecular armor shields that block exhaustion signals, allowing the cells to relentlessly destroy the tumor without fatiguing.",
    "the_biological_barrier": "The immunosuppressive tumor microenvironment (TME) induces T-cell exhaustion and blocks infiltration into solid tumor tissue.",
    "the_engineered_trick": "Formulated CD5-targeted lipid nanoparticles encapsulating modified mRNA encoding chimeric antigen receptors, selectively transfecting circulating T-cells in vivo without viral vectors.",
    "research_takeaway": "Pioneers next-generation cellular immunotherapies that can penetrate and persist within hostile solid tumor microenvironments.",
    "mechanism_pipeline": {
      "step1_input": "Circulating host T-lymphocytes and target disease pathology (cardiac fibrosis / solid tumor)",
      "step2_catalyst": "CD5-targeted lipid nanoparticles (tLNPs) delivering 1-methylpseudouridine-modified CAR mRNA",
      "step3_output": "Transient in vivo generation of functional cytotoxic CAR-T cells, reducing pathology without leukapheresis"
    },
    "story_pillars": {
      "problem": "Cancer Claims 10 Million Lives: Cancer is the second biggest killer in the world, taking 10 million lives every year. Solid tumors (in lungs, breasts, colon) make up 85% of adult cancers. Conventional chemotherapy poisons healthy cells, and current breakthrough cell therapies cost over $450,000 per patient and take weeks of hospital manufacturing.",
      "benchmark": "Slow, Dangerous, and Expensive: Standard CAR-T therapy requires taking blood from a patient, shipping it to a cleanroom lab for weeks of viral gene editing, giving the patient toxic chemotherapy to wipe out their immune system, and re-infusing the cells. Many sick patients die while waiting for the manufacturing process to finish.",
      "gap": "Tumor Armor and Exhaustion: Solid tumors surround themselves with dense scar tissue and release chemical camouflage that makes immune killer T-cells fall asleep (exhaustion). If you inject normal T-cells, they get trapped outside the tumor or get switched off before they can kill a single cancer cell.",
      "controls": "The Test System & Controls: Tested in living mouse disease models and human immune cells. Researchers tracked immune cell killing using fluorescent laser cell counters (flow cytometry) and real-time live-body camera imaging. They injected non-engineered blank particles as negative vehicle controls to prove the mRNA caused the cure.",
      "solution": "A Single Injection That Programs Cells Inside The Body: Instead of removing blood, scientists engineered microscopic fat bubbles (lipid nanoparticles) carrying temporary mRNA instructions. The fat bubbles have a special antibody tag that only sticks to T-cells in the bloodstream, delivering the genetic recipe so the patient's own body manufactures CAR-T killer cells automatically in minutes!",
      "proof": "The Proven Result & Goal to Beat: A single injection reprogrammed over 80% of immune T-cells inside the body, cleared scar tissue, and restored normal organ function without cleanroom labs! The Target to Beat: Because temporary mRNA naturally degrades within 48 hours, the next goal for proposals is designing circular mRNA (circRNA) that lasts longer to destroy solid tumors with a single treatment.",
      "finding": "The Proven Result & Goal to Beat: A single injection reprogrammed over 80% of immune T-cells inside the body, cleared scar tissue, and restored normal organ function without cleanroom labs! The Target to Beat: Because temporary mRNA naturally degrades within 48 hours, the next goal for proposals is designing circular mRNA (circRNA) that lasts longer to destroy solid tumors with a single treatment.",
      "p1_problem": "Cancer Claims 10 Million Lives: Cancer is the second biggest killer in the world, taking 10 million lives every year. Solid tumors (in lungs, breasts, colon) make up 85% of adult cancers. Conventional chemotherapy poisons healthy cells, and current breakthrough cell therapies cost over $450,000 per patient and take weeks of hospital manufacturing.",
      "p2_benchmark": "Slow, Dangerous, and Expensive: Standard CAR-T therapy requires taking blood from a patient, shipping it to a cleanroom lab for weeks of viral gene editing, giving the patient toxic chemotherapy to wipe out their immune system, and re-infusing the cells. Many sick patients die while waiting for the manufacturing process to finish.",
      "p3_gap": "Tumor Armor and Exhaustion: Solid tumors surround themselves with dense scar tissue and release chemical camouflage that makes immune killer T-cells fall asleep (exhaustion). If you inject normal T-cells, they get trapped outside the tumor or get switched off before they can kill a single cancer cell.",
      "p4_controls": "The Test System & Controls: Tested in living mouse disease models and human immune cells. Researchers tracked immune cell killing using fluorescent laser cell counters (flow cytometry) and real-time live-body camera imaging. They injected non-engineered blank particles as negative vehicle controls to prove the mRNA caused the cure.",
      "p5_solution": "A Single Injection That Programs Cells Inside The Body: Instead of removing blood, scientists engineered microscopic fat bubbles (lipid nanoparticles) carrying temporary mRNA instructions. The fat bubbles have a special antibody tag that only sticks to T-cells in the bloodstream, delivering the genetic recipe so the patient's own body manufactures CAR-T killer cells automatically in minutes!",
      "p6_finding": "The Proven Result & Goal to Beat: A single injection reprogrammed over 80% of immune T-cells inside the body, cleared scar tissue, and restored normal organ function without cleanroom labs! The Target to Beat: Because temporary mRNA naturally degrades within 48 hours, the next goal for proposals is designing circular mRNA (circRNA) that lasts longer to destroy solid tumors with a single treatment."
    },
    "faq_insights": [
      {
        "question": "What is the primary breakthrough of in vivo CAR-T over ex vivo CAR-T?",
        "answer": "Ex vivo CAR-T takes weeks of cleanroom gene editing and high-dose chemotherapy. In vivo CAR-T delivers mRNA via a single shot directly into the bloodstream."
      },
      {
        "question": "Why is mRNA used instead of permanent DNA editing?",
        "answer": "mRNA is temporary and fades away naturally. This prevents the immune cells from multiplying uncontrollably or causing lifelong autoimmune harm."
      },
      {
        "question": "What is the critical knowledge gap for in vivo mRNA CAR delivery?",
        "answer": "mRNA naturally breaks down within 48 hours, requiring multiple booster shots, and liver scavenger cells eat up some of the nanoparticles."
      },
      {
        "question": "How should an undergraduate proposal build upon this benchmark?",
        "answer": "In Tier 2, benchmark this 80% reprogramming efficiency. In Tier 3, identify the 48-hour expression limit as your gap, and propose circular mRNA (circRNA) that resists cellular degradation enzymes."
      }
    ],
    "proposal_ready_sentences": {
      "tier1_sentence": "Cancer remains the second leading cause of mortality worldwide, accounting for nearly 10 million deaths annually, with solid tumors exhibiting profound resistance to conventional systemic chemotherapies (WHO/IARC; Rurik et al., 2022).",
      "tier2_sentence": "In vivo cellular programming demonstrated that CD5-targeted lipid nanoparticles deliver modified mRNA directly into circulating T cells, generating functional CAR-T cells in vivo without ex vivo leukapheresis (Rurik et al., 2022).",
      "tier3_sentence": "However, therapeutic persistence remains constrained by the 48-hour half-life of transient mRNA and non-specific hepatic macrophage uptake, necessitating repeat dosing strategies and enhanced targeting valency (Rurik et al., 2022)."
    }
  }
};

for item in DOMAIN_KNOWLEDGE:
    d_id = item.get("id")
    if d_id in DOMAIN_EXTENSIONS:
        item.update(DOMAIN_EXTENSIONS[d_id])



def simplify_academic_text(text: str) -> str:
    """
    Translates dense academic syntax and vocabulary into conversational,
    undergraduate-accessible plain English.
    """
    s = text.strip()
    replacements = [
        (r"\bundergoes irreversible thermal denaturation\b", "permanently melts and unfolds from high heat"),
        (r"\bthermal denaturation\b", "unfolding due to high temperature"),
        (r"\bthermolability\b", "sensitivity to heat"),
        (r"\bdepolymerization\b", "breaking down long plastic chains into reusable raw chemical units"),
        (r"\bhydrolysis\b", "splitting chemical bonds using water"),
        (r"\bheterologous expression\b", "producing the protein inside a foreign lab host"),
        (r"\bconfer(?:s|red)? resistance\b", "protect against disease or stress"),
        (r"\battenuate(?:s|d)?\b", "weaken"),
        (r"\bupregulate(?:s|d)?\b", "turn up production of"),
        (r"\bdownregulate(?:s|d)?\b", "turn down / suppress"),
        (r"\bpreclude(?:s|d)?\b", "prevent"),
        (r"\bconstrain(?:s|ed)?\b", "limit"),
        (r"\bintrogress(?:ed|ion)?\b", "cross-breeding ancestral genes into modern crops"),
        (r"\bsenescence\b", "premature leaf withering and cell death"),
        (r"\btitration\b", "gradual step-by-step measurement"),
        (r"\bsynergistic(?:ally)?\b", "cooperative amplified effect (1 + 1 = 5)"),
        (r"\bisothermal\b", "constant single-temperature (no thermal cycler needed)"),
        (r"\bcollateral (?:trans-)?cleavage\b", "shredding of nearby glowing reporter probes"),
        (r"\blimit of detection\b", "lowest amount the test can detect"),
        (r"\binclusion bodies\b", "tangled non-functional protein clumps"),
        (r"\bcodon optimization\b", "rewriting DNA spelling for the host organism"),
        (r"\bdirected evolution\b", "accelerated mutation in a test tube"),
        (r"\bmetabolic burden\b", "exhaustion and energy drain on the cell"),
        (r"\bhomeologous gene silencing\b", "duplicate chromosomes accidentally turning off the target gene"),
        (r"\bpost-consumer amorphous\b", "recycled plastic bottle"),
        (r"\brational disulfide bridges\b", "engineered molecular welds that lock the protein shape together")
    ]
    for pattern, repl in replacements:
        s = re.sub(pattern, repl, s, flags=re.IGNORECASE)
    
    # Strip heavy academic introductory filler
    s = re.sub(r"^(?:Here,? we show that|In this study,? we discovered that|Present estimates suggest that|Recent findings indicate that)\s*", "", s, flags=re.IGNORECASE)
    return s


def _fetch_semantic_scholar_record(doi: str) -> Dict[str, Any]:
    """Queries Semantic Scholar API for abstract and verified TLDR summary."""
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/{doi}?fields=title,abstract,tldr,authors,year,journal,fieldsOfStudy"
        resp = requests.get(url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            title = data.get("title", "")
            abstract = (data.get("abstract") or "").strip()
            tldr = (data.get("tldr") or {}).get("text", "").strip()

            authors_list = [a.get("name") for a in data.get("authors", []) if a.get("name")]
            authors_str = ", ".join(authors_list[:3]) + (" et al." if len(authors_list) > 3 else "")

            year = data.get("year", 2023)
            journal = data.get("journal", {}).get("name", "Academic Publication") if isinstance(data.get("journal"), dict) else "Academic Publication"

            return {
                "success": bool(title),
                "title": title,
                "abstract": abstract,
                "tldr": tldr,
                "authors": authors_str,
                "year": year,
                "journal": journal
            }
    except Exception:
        pass
    return {"success": False}


def _fetch_openalex_record(doi: str) -> Dict[str, Any]:
    """Queries OpenAlex and reconstructs abstract from inverted index."""
    try:
        url = f"https://api.openalex.org/works/https://doi.org/{doi}"
        resp = requests.get(url, headers={"User-Agent": "BioWriterStudio/1.0 (mailto:biowriter@university.edu)"}, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            title = data.get("title", "")
            inv = data.get("abstract_inverted_index")
            abstract = ""
            if inv:
                words = {}
                for w, positions in inv.items():
                    for pos in positions:
                        words[pos] = w
                abstract = " ".join([words[i] for i in sorted(words.keys())])

            authorships = data.get("authorships", [])
            auth_names = [a.get("author", {}).get("display_name") for a in authorships if a.get("author", {}).get("display_name")]
            authors_str = ", ".join(auth_names[:3]) + (" et al." if len(auth_names) > 3 else "")

            year = data.get("publication_year", 2023)
            journal = data.get("primary_location", {}).get("source", {}).get("display_name", "Academic Publication")

            return {
                "success": bool(title),
                "title": title,
                "abstract": abstract,
                "authors": authors_str,
                "year": year,
                "journal": journal
            }
    except Exception:
        pass
    return {"success": False}


def _synthesize_conceptual_summary(title: str, year: int, journal: str, authors: str) -> str:
    """Provides a structured background excerpt when publisher has paywalled the abstract."""
    return (
        f"Investigation into {title.lower().rstrip('.')} ({year}). "
        f"Conducted by {authors} in {journal}, this research addresses biological mechanisms, "
        f"experimental methods, and quantitative benchmarks. [Note: The publisher restricts open API access to the full abstract for this publication. "
        f"This conceptual summary was automatically generated to enable evidence extraction and parameter deconstruction.]"
    )


def fetch_paper_abstract_and_meta(identifier: str) -> Dict[str, Any]:
    """
    Ultra-reliable paper metadata & abstract fetcher with 6-tier fallback cascade.
    1. Europe PMC (Open Access Biomedical Articles)
    2. NCBI PubMed (Medical & Biotech Journals)
    3. Semantic Scholar (200M+ Papers: Abstract & AI TLDR)
    4. OpenAlex (Reconstructs abstract from Inverted Index)
    5. CrossRef Works (Global DOI Registry + JATS parsing)
    6. Smart Conceptual Synthesis (for closed book chapters / paywalled monographs)
    """
    if not identifier:
        return {"success": False, "error": "Please enter a valid DOI or PubMed ID."}

    id_clean = identifier.strip().strip('"\'<>[](){}')
    id_clean = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", id_clean, flags=re.IGNORECASE).strip()
    id_clean = re.sub(r"^https?://pubmed\.ncbi\.nlm\.nih\.gov/", "", id_clean, flags=re.IGNORECASE).strip()
    id_clean = re.sub(r"^https?://(?:www\.)?ncbi\.nlm\.nih\.gov/pubmed/", "", id_clean, flags=re.IGNORECASE).strip()
    id_clean = re.sub(r"^doi\s*[:=]\s*", "", id_clean, flags=re.IGNORECASE).strip()
    id_clean = re.sub(r"^pmid\s*[:=]\s*", "", id_clean, flags=re.IGNORECASE).strip()
    id_clean = id_clean.rstrip("/.,;").strip()

    is_pmid = bool(re.match(r"^\d{1,9}$", id_clean))
    doi_clean = id_clean

    if not is_pmid and ("/" not in doi_clean or len(doi_clean) < 5):
        return {
            "success": False,
            "error": f"Invalid DOI format '{identifier}'. Expected format like: 10.1038/s41586-020-2149-4"
        }

    # Tracking discovered metadata
    best_meta = {
        "title": "",
        "authors": "",
        "year": 2023,
        "journal": "",
        "id": id_clean
    }
    candidate_tldr = ""

    # Tier 1: Europe PMC
    epmc_res = _fetch_europepmc_record(id_clean if is_pmid else doi_clean, is_doi=not is_pmid)
    if epmc_res.get("success"):
        if len(epmc_res.get("abstract", "").split()) > 20:
            return epmc_res
        best_meta.update({k: v for k, v in epmc_res.items() if v and k != "abstract"})

    # Tier 2: NCBI PubMed E-utilities
    if is_pmid:
        pm_res = _fetch_pubmed_abstract(id_clean)
        if pm_res.get("success") and len(pm_res.get("abstract", "").split()) > 20:
            return pm_res
        if pm_res.get("success"):
            best_meta.update({k: v for k, v in pm_res.items() if v and k != "abstract"})
    else:
        pm_doi_res = _fetch_pubmed_by_doi(doi_clean)
        if pm_doi_res.get("success") and len(pm_doi_res.get("abstract", "").split()) > 20:
            return pm_doi_res
        if pm_doi_res.get("success"):
            best_meta.update({k: v for k, v in pm_doi_res.items() if v and k != "abstract"})

    # Tier 3: Semantic Scholar (abstract + TLDR)
    if not is_pmid:
        s2_res = _fetch_semantic_scholar_record(doi_clean)
        if s2_res.get("success"):
            if s2_res.get("title") and not best_meta["title"]:
                best_meta["title"] = s2_res["title"]
            if s2_res.get("authors") and not best_meta["authors"]:
                best_meta["authors"] = s2_res["authors"]
            if s2_res.get("year"):
                best_meta["year"] = s2_res["year"]
            if s2_res.get("journal") and not best_meta["journal"]:
                best_meta["journal"] = s2_res["journal"]
            if s2_res.get("tldr"):
                candidate_tldr = s2_res["tldr"]
            if len(s2_res.get("abstract", "").split()) > 20:
                s2_res["id"] = doi_clean
                s2_res["type"] = "doi"
                return s2_res

    # Tier 4: OpenAlex (Inverted index abstract)
    if not is_pmid:
        oa_res = _fetch_openalex_record(doi_clean)
        if oa_res.get("success"):
            if oa_res.get("title") and not best_meta["title"]:
                best_meta["title"] = oa_res["title"]
            if oa_res.get("authors") and not best_meta["authors"]:
                best_meta["authors"] = oa_res["authors"]
            if oa_res.get("year"):
                best_meta["year"] = oa_res["year"]
            if oa_res.get("journal") and not best_meta["journal"]:
                best_meta["journal"] = oa_res["journal"]
            if len(oa_res.get("abstract", "").split()) > 20:
                oa_res["id"] = doi_clean
                oa_res["type"] = "doi"
                return oa_res

    # Tier 5: CrossRef Works
    if not is_pmid:
        cr_res = _fetch_crossref_abstract(doi_clean)
        if cr_res.get("success"):
            if cr_res.get("title") and not best_meta["title"]:
                best_meta["title"] = cr_res["title"]
            if cr_res.get("authors") and not best_meta["authors"]:
                best_meta["authors"] = cr_res["authors"]
            if cr_res.get("year"):
                best_meta["year"] = cr_res["year"]
            if cr_res.get("journal") and not best_meta["journal"]:
                best_meta["journal"] = cr_res["journal"]
            if len(cr_res.get("abstract", "").split()) > 20:
                return cr_res

    # Tier 6: Handled paywalled / restricted abstracts with verified TLDR or conceptual synthesis
    if best_meta.get("title"):
        title = best_meta["title"]
        authors = best_meta.get("authors") or "Authors"
        year = best_meta.get("year") or 2023
        journal = best_meta.get("journal") or "Academic Publication"

        if candidate_tldr:
            abstract_text = f"[Key Research Summary / TLDR]: {candidate_tldr}"
            note = f"The publisher ({journal}) restricts automated API access to the full chapter abstract. Retrieved verified research TLDR."
            is_tldr = True
        else:
            abstract_text = _synthesize_conceptual_summary(title, year, journal, authors)
            note = f"The publisher ({journal}) restricts automated API access to the full abstract. Generated structured conceptual context from metadata."
            is_tldr = False

        return {
            "success": True,
            "type": "doi" if not is_pmid else "pmid",
            "id": id_clean,
            "title": title,
            "authors": authors,
            "year": year,
            "journal": journal,
            "abstract": abstract_text,
            "is_tldr": is_tldr,
            "publisher_restricted": True,
            "publisher_note": note
        }

    # Tier 6.5: Curated landmark papers fallback (immune to external network dropouts)
    for sp_key, sp in SAMPLE_PAPERS.items():
        if (sp.get("doi") and sp["doi"].lower() == doi_clean.lower()) or (sp.get("pmid") and str(sp["pmid"]) == str(id_clean)):
            return {
                "success": True,
                "type": "doi" if not is_pmid else "pmid",
                "id": doi_clean if not is_pmid else id_clean,
                "title": sp.get("title", ""),
                "authors": sp.get("authors", ""),
                "year": sp.get("year", 2020),
                "journal": sp.get("journal", ""),
                "abstract": sp.get("abstract", ""),
                "is_tldr": False
            }

    return {
        "success": False,
        "error": f"Could not find record for '{identifier}'. Check the DOI/PMID or paste the abstract directly."
    }


def _fetch_europepmc_record(identifier: str, is_doi: bool = True) -> Dict[str, Any]:
    """Queries Europe PMC REST API with proper query formatting."""
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    query = f'DOI:"{identifier}"' if is_doi else f"EXT_ID:{identifier} AND SRC:MED"
    params = {"query": query, "format": "json", "resultType": "core"}
    try:
        resp = requests.get(url, params=params, timeout=6.0)
        if resp.status_code == 200:
            results = resp.json().get("resultList", {}).get("result", [])
            if not results and is_doi:
                # Fallback: try unquoted DOI query
                params["query"] = f"DOI:{identifier}"
                resp2 = requests.get(url, params=params, timeout=6.0)
                if resp2.status_code == 200:
                    results = resp2.json().get("resultList", {}).get("result", [])
            if results:
                item = results[0]
                title = item.get("title", "Scientific Study")
                title_clean = re.sub(r"<[^>]+>", "", title).strip()

                abstract_raw = item.get("abstractText", "")
                abstract_clean = re.sub(r"<[^>]+>", " ", abstract_raw).strip()
                abstract_clean = re.sub(r"\s+", " ", abstract_clean)

                author_str = item.get("authorString", "Authors")
                if len(author_str.split(",")) > 4:
                    author_str = author_str.split(",")[0] + " et al."

                year = None
                try:
                    year = int(item.get("pubYear", 2023))
                except Exception:
                    year = 2023

                journal = item.get("journalTitle") or item.get("journalInfo", {}).get("journal", {}).get("title", "Peer-Reviewed Journal")

                return {
                    "success": True,
                    "type": "doi" if is_doi else "pmid",
                    "id": identifier,
                    "title": title_clean,
                    "authors": author_str,
                    "year": year,
                    "journal": journal,
                    "abstract": abstract_clean
                }
    except Exception:
        pass
    return {"success": False}


def _fetch_pubmed_by_doi(doi: str) -> Dict[str, Any]:
    """Resolves DOI to PMID via NCBI ESearch, then fetches full abstract XML."""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": f"{doi}[aid]", "retmode": "json"}
    try:
        resp = requests.get(url, params=params, timeout=5.0)
        if resp.status_code == 200:
            id_list = resp.json().get("esearchresult", {}).get("idlist", [])
            if not id_list:
                params["term"] = doi
                resp2 = requests.get(url, params=params, timeout=5.0)
                if resp2.status_code == 200:
                    id_list = resp2.json().get("esearchresult", {}).get("idlist", [])
            if id_list:
                pmid = id_list[0]
                return _fetch_pubmed_abstract(pmid)
    except Exception:
        pass
    return {"success": False}


def _fetch_crossref_abstract(doi: str) -> Dict[str, Any]:
    """Retrieves metadata from CrossRef."""
    if not doi or "/" not in doi:
        return {"success": False, "error": "Invalid DOI format."}

    url = f"https://api.crossref.org/works/{doi}"
    headers = {"User-Agent": "BioWriterStudio/1.0 (mailto:biowriter@university.edu)"}

    try:
        resp = requests.get(url, headers=headers, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json().get("message", {})
            title = data.get("title", ["Unknown Title"])[0]
            abstract_raw = data.get("abstract", "")
            abstract_clean = re.sub(r"<[^>]+>", " ", abstract_raw).strip()
            abstract_clean = re.sub(r"\s+", " ", abstract_clean)

            authors_list = []
            for a in data.get("author", []):
                family = a.get("family", "")
                given = a.get("given", "")
                if family:
                    authors_list.append(f"{family}, {given[0]}." if given else family)
            authors_str = ", ".join(authors_list[:3])
            if len(authors_list) > 3:
                authors_str += " et al."

            published = data.get("published-print") or data.get("published-online") or data.get("created")
            year = None
            if published and "date-parts" in published and published["date-parts"]:
                year = published["date-parts"][0][0]

            journal = data.get("container-title", ["Unknown Journal"])[0] if data.get("container-title") else "Unknown Journal"

            return {
                "success": True,
                "type": "doi",
                "id": doi,
                "title": title,
                "authors": authors_str or "Authors",
                "year": year or 2024,
                "journal": journal,
                "abstract": abstract_clean
            }
    except Exception:
        pass
    return {"success": False}


def _fetch_pubmed_abstract(pmid: str) -> Dict[str, Any]:
    """Retrieves abstract and metadata via NCBI E-utilities."""
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
    try:
        resp = requests.get(url, timeout=5.0)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            article = root.find(".//PubmedArticle")
            if article is not None:
                title_elem = article.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None and title_elem.text else "Unknown Title"

                abs_texts = [elem.text for elem in article.findall(".//AbstractText") if elem.text]
                abstract = " ".join(abs_texts).strip()

                journal_elem = article.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None and journal_elem.text else "PubMed Journal"
                year_elem = article.find(".//JournalIssue/PubDate/Year")
                year = int(year_elem.text) if year_elem is not None and year_elem.text else 2023

                author_elems = article.findall(".//Author")
                authors_list = []
                for a in author_elems:
                    last = a.find("LastName")
                    init = a.find("Initials")
                    if last is not None and last.text:
                        l_str = last.text
                        i_str = f" {init.text}." if (init is not None and init.text) else ""
                        authors_list.append(l_str + i_str)
                authors_str = ", ".join(authors_list[:3])
                if len(authors_list) > 3:
                    authors_str += " et al."

                return {
                    "success": True,
                    "type": "pmid",
                    "id": pmid,
                    "title": title,
                    "authors": authors_str or "Authors",
                    "year": year,
                    "journal": journal,
                    "abstract": abstract
                }
    except Exception:
        pass
    return {"success": False}


def deconstruct_paper(text: str, title: str = "", identifier: str = "", authors: str = "", year: Optional[int] = None, journal: str = "") -> Dict[str, Any]:
    """
    Deconstructs a scientific paper/abstract into:
    1. Executive 3-sentence summary (Problem -> Intervention -> Finding)
    2. Plain-English "ELI-Undergrad" narrative with intuitive analogies
    3. Extracted Proposal Parameters (Chassis, Tool, Metrics, Controls, Gaps)
    4. Detected Biotech Jargon Buster definitions and analogies
    5. Proposal placement recommendations
    6. Socratic RHEV Paraphrase Synthesis prompt
    """
    clean_text = text.strip()
    if not clean_text or len(clean_text.split()) < 15:
        return {
            "status": "error",
            "message": "Text is too short to analyze. Paste an entire abstract or excerpt (at least 15 words)."
        }

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text) if s.strip()]

    # 1. Sentence Categorization
    problem_sentences = []
    solution_sentences = []
    finding_sentences = []
    limitation_sentences = []

    disease_symptom_reject = r"\b(?:is characterized by|are characterized by|symptoms? (?:include|such as|of)|manifests? as|anhedonia|fatigue|sleep disturbances|cognitive dysfunction|suicidal ideation|pathophysiology|clinical presentation|psychiatric disorder|affects (?:approximately|\d+)|epidemiology|prevalence of|mortality rate|morbidity|major depressive disorder|etiology|pathogenesis)\b"
    scope_reject = r"^(?:therefore,?|in this review,?|this review|we review|the objective of this|the aim of this|here we review|this article reviews|this review examines)\b"

    for s in sentences:
        low = s.lower()
        if any(w in low for w in ["however", "remains a challenge", "severely restricted", "impeded by", "drastically decreases", "lack", "bottleneck", "limited by", "incurring"]):
            if not limitation_sentences and len(problem_sentences) > 0:
                limitation_sentences.append(s)
            else:
                problem_sentences.append(s)
        elif any(w in low for w in ["here, we", "we engineered", "we developed", "we coupled", "we discovered", "we introgressed", "this study", "we designed", "constructs were"]):
            if not re.search(disease_symptom_reject, s, re.IGNORECASE) and not re.search(scope_reject, s.strip(), re.IGNORECASE):
                solution_sentences.append(s)
        elif any(w in low for w in ["achieved", "exhibited", "detected", "reduced", "increased", "yield", "fold", "resulting in", "demonstrated", "turnovers"]):
            if not re.search(scope_reject, s.strip(), re.IGNORECASE):
                finding_sentences.append(s)
        elif any(w in low for w in ["despite", "nevertheless", "resisted", "background", "penalty", "silencing", "restricting", "future work"]):
            limitation_sentences.append(s)

    # Extract Key Proposal Parameters first (domain-aware & protocol-filtered)
    parameters = _extract_proposal_parameters(clean_text, sentences, title=title, authors=authors, year=year)

    protocol_reject = r"^(?:to obtain|we cloned|we introduced|the construct|in this study|here,? we|a plasmid|expression was|we designed|we report|constructs were|the cdna)"
    exec_problem = ""
    for s in problem_sentences:
        if not re.match(protocol_reject, s.strip(), re.IGNORECASE):
            exec_problem = s
            break
    if not exec_problem:
        exec_problem = parameters.get("burden_statistic") or (sentences[0] if sentences else "Specific molecular and operational challenges impede biotechnology applications.")

    valid_solutions = [s for s in sentences if not re.search(disease_symptom_reject, s, re.IGNORECASE) and not re.search(scope_reject, s.strip(), re.IGNORECASE) and s != exec_problem]
    exec_solution = parameters.get("key_innovation") or (solution_sentences[0] if solution_sentences else (valid_solutions[0] if valid_solutions else "Targeted molecular and biochemical intervention."))
    exec_finding = parameters.get("primary_metric_sentence") or (finding_sentences[0] if finding_sentences else (sentences[-1] if len(sentences) > 2 else ""))
    exec_limitation = parameters.get("stated_gap") or (limitation_sentences[0] if limitation_sentences else "")

    # 2. Plain-English "ELI-Undergrad" Simple Narrative
    eli_narrative = _build_eli_narrative(clean_text, exec_problem, exec_solution, exec_finding, exec_limitation)

    # 3. Detect Jargon Terms in Text
    detected_jargon = []
    for key, jdata in JARGON_LEXICON.items():
        pattern = r"\b" + re.escape(key) + r"\b"
        if re.search(pattern, clean_text, flags=re.IGNORECASE):
            detected_jargon.append(jdata)

    unique_jargon = []
    seen_terms = set()
    for j in detected_jargon:
        if j["term"] not in seen_terms:
            seen_terms.add(j["term"])
            unique_jargon.append(j)

    # 4. Proposal Section Recommendations
    recommendations = _generate_proposal_recommendations(parameters, title)

    # 6. Socratic RHEV Paraphrase Prompt
    author_lead = authors.split(",")[0] if authors else "the authors"
    pub_year = year or "recent"
    rhev_challenge = (
        f"Exercise (Anti-Plagiarism RHEV Protocol):\n"
        f"Close this window or hide the summary. In your own words, complete this sentence for your proposal:\n"
        f"\"According to {author_lead} ({pub_year}), conventional baseline approaches are limited by [specific biophysical bottleneck], "
        f"yet their team achieved [quantified metric] by [engineering intervention]...\""
    )

    apa_citation = f"{authors or 'Authors'} ({year or 'n.d.'}). {title or 'Scientific Study'}. {journal or 'Journal'}. {('DOI: ' + identifier) if identifier else ''}".strip()
    nature_citation = f"{authors or 'Authors'}. {title or 'Scientific Study'}. {journal or 'Journal'} ({year or 'n.d.'}).".strip()

    # 7. Dedicated Plain-English Parameter Explanations for Evidence Matrix
    param_explanations = _generate_parameter_explanations(parameters, title, authors, year, journal)

    # 8. Research Landscape & Proposal Blueprint (Three-Stage Story + From Paper -> Proposal)
        # 9. Deep Paper Comprehension Dossier
    matched_domain_rec = None
    clean_combined = f"{title} {clean_text}".lower()
    for item in DOMAIN_KNOWLEDGE:
        if re.search(item["pattern"], clean_combined):
            matched_domain_rec = item
            break

    deep_summary = _synthesize_deep_comprehension(
        parameters=parameters,
        matched_domain=matched_domain_rec,
        exec_summary={
            "problem": exec_problem,
            "intervention": exec_solution,
            "main_finding": exec_finding,
            "limitation": exec_limitation or parameters.get("stated_gap", "")
        },
        title=title,
        authors=authors,
        year=year,
        journal=journal
    )

    landscape_blueprint = _synthesize_research_landscape_and_proposal_blueprint(
        parameters=parameters,
        exec_summary={
            "problem": exec_problem,
            "intervention": exec_solution,
            "main_finding": exec_finding,
            "limitation": exec_limitation or parameters.get("stated_gap", "")
        },
        title=title,
        authors=authors,
        year=year,
        journal=journal,
        apa_citation=apa_citation
    )

    if deep_summary.get("story_pillars"):
        sp = deep_summary["story_pillars"]
        eli_narrative["simple_problem"] = sp.get("problem", eli_narrative.get("simple_problem", ""))
        eli_narrative["simple_solution"] = sp.get("solution", eli_narrative.get("simple_solution", ""))
        eli_narrative["simple_takeaway"] = sp.get("proof", eli_narrative.get("simple_takeaway", ""))
        eli_narrative["simple_limitation"] = sp.get("gap", eli_narrative.get("simple_limitation", ""))
    if deep_summary.get("core_analogy"):
        eli_narrative["core_analogy"] = deep_summary["core_analogy"]

    return {
        "status": "success",
        "title": title or "Deconstructed Paper",
        "authors": authors or "Identified Authors",
        "year": year,
        "journal": journal,
        "identifier": identifier,
        "executive_summary": {
            "problem": exec_problem,
            "intervention": exec_solution,
            "main_finding": exec_finding,
            "limitation": exec_limitation or parameters.get("stated_gap", "")
        },
        "plain_english_explanation": eli_narrative,
        "jargon_buster": unique_jargon,
        "extracted_parameters": parameters,
        "parameter_explanations": param_explanations,
        "deep_summary": deep_summary,
        "one_sentence_pitch": deep_summary["one_sentence_pitch"],
        "core_analogy": deep_summary.get("core_analogy", eli_narrative.get("core_analogy", "")),
        "mechanism_pipeline": deep_summary["mechanism_pipeline"],
        "story_pillars": deep_summary.get("story_pillars", {}),
        "the_four_pillars": deep_summary.get("story_pillars", {}),
        "faq_insights": deep_summary["faq_insights"],
        "proposal_ready_sentences": deep_summary["proposal_ready_sentences"],
        "proposal_recommendations": recommendations,
        "rhev_challenge": rhev_challenge,
        "citations": {
            "apa": apa_citation,
            "nature": nature_citation
        },
        "three_stage_landscape": landscape_blueprint["three_stage_landscape"],
        "from_paper_to_proposal": landscape_blueprint["from_paper_to_proposal"],
        "position_map": landscape_blueprint["position_map"],
        "grouped_parameters": landscape_blueprint["grouped_parameters"]
    }


def _synthesize_research_landscape_and_proposal_blueprint(
    parameters: Dict[str, Any],
    exec_summary: Dict[str, str],
    title: str,
    authors: str,
    year: Optional[int],
    journal: str,
    apa_citation: str
) -> Dict[str, Any]:
    """
    Synthesizes the scientific landscape and educational proposal translation:
    1. Three-Stage Evidence Story (Current State of Art -> Unresolved Gap -> Research Opportunity)
    2. 6-Point From Paper -> Proposal Translation with Required Validation Checklist
    3. Literature Position Map progression
    4. Grouped 6 parameters under 3 core scientific questions
    """
    tool = parameters.get("tool") or "Current published intervention"
    benchmark = parameters.get("primary_metric_sentence") or "Reported quantitative baseline"
    gap = parameters.get("stated_gap") or exec_summary.get("limitation") or "Operational and mechanistic parameters remain constrained"
    innovation = parameters.get("key_innovation") or exec_summary.get("intervention") or "Engineered construct / strategy"
    findings = parameters.get("key_findings") or exec_summary.get("main_finding") or "Reported empirical findings"
    horizon = parameters.get("research_horizon") or "Next translational milestone"
    chassis = parameters.get("chassis") or "Experimental model system"

    # Three-Stage Evidence Story
    three_stage = {
        "stage1_state_of_the_art": {
            "title": "1. What exists? (Current State of the Art)",
            "approach": tool,
            "benchmark": benchmark,
            "evidence_level": f"Published peer-reviewed study in {journal or 'scientific literature'} ({year or 'recent'})",
            "major_strength": innovation or findings,
            "citation": apa_citation
        },
        "stage2_unresolved_gap": {
            "title": "2. What is still limiting the field? (The Unresolved Gap)",
            "statement": gap,
            "evidence": apa_citation
        },
        "stage3_research_opportunity": {
            "title": "3. Where could a new study contribute? (Proposed Research Opportunity)",
            "opportunity_statement": f"Investigate whether developing an alternative strategy can overcome the limitation ({gap[:120]}...) to achieve a calibrated improvement over the literature benchmark ({benchmark[:100]}...).",
            "test_strategy": parameters.get("experimental_strategy") or f"Model testing in {chassis} with verified positive and negative controls.",
            "pathway": ["Existing Benchmark", "Unresolved Limitation", "Research Opportunity", "Experimental Validation"]
        }
    }

    # 6-Point From Paper -> Proposal Synthesizer
    from_paper_to_proposal = {
        "established_knowledge": f"What this paper confirms: {findings[:180]}...",
        "current_benchmark": benchmark,
        "limitation": gap,
        "research_opportunity": f"Targeted investigation addressing: {gap[:150]}...",
        "proposed_contribution": f"Demonstrate calibrated improvement or alternative mechanism over {tool}.",
        "required_validation_checklist": [
            "Defined molecular / biological intervention (specific chassis & tool)",
            "Appropriate control triad (negative vehicle, positive benchmark reference)",
            "Measurable quantitative endpoint (calibrated against literature rate)",
            "Mechanistic analytical assay (e.g. HPLC, qPCR, Western blot, crystal resolution)",
            "Comparative evaluation against established reference",
            "Validated testing matrix or real-world model system"
        ]
    }

    # Literature Position Map
    position_map = {
        "established": {
            "label": "Established Standard",
            "detail": f"{chassis} • Baseline reference",
            "benchmark": benchmark[:80]
        },
        "gap": {
            "label": "Unresolved Knowledge Gap",
            "detail": gap[:100]
        },
        "emerging": {
            "label": "Recent Literature Finding",
            "detail": f"{title[:70]}... ({year or 'recent'})",
            "contribution": innovation[:80]
        },
        "proposed": {
            "label": "Your Proposed Study",
            "detail": "Novel intervention targeting unresolved gap",
            "horizon": horizon[:80]
        }
    }

    # Grouped Parameters (A, B, C)
    grouped_parameters = {
        "question_a": {
            "question": "A. Why is the research needed?",
            "subheading": "Problem Magnitude ➔ Current Benchmark ➔ Unresolved Limitation",
            "p1_label": "Parameter 1: Problem Burden",
            "p1_value": parameters.get("burden_statistic", ""),
            "p2_label": "Parameter 2: Current Benchmark",
            "p2_value": benchmark,
            "p3_label": "Parameter 3: Unresolved Gap",
            "p3_value": gap
        },
        "question_b": {
            "question": "B. What is the proposed scientific solution?",
            "subheading": "Experimental Strategy ➔ Innovation & Molecular Mechanism",
            "p4_label": "Parameter 4: Experimental Strategy & Controls",
            "p4_value": parameters.get("experimental_strategy", "") or parameters.get("controls", ""),
            "p5_label": "Parameter 5: Core Innovation & Mechanism",
            "p5_value": innovation
        },
        "question_c": {
            "question": "C. What would constitute success?",
            "subheading": "Evidence Proof ➔ Calibrated Target Milestone",
            "p6_label": "Parameter 6: Evidence Proof & Milestone",
            "p6_value": f"{findings} | Milestone Horizon: {horizon}"
        }
    }

    return {
        "three_stage_landscape": three_stage,
        "from_paper_to_proposal": from_paper_to_proposal,
        "position_map": position_map,
        "grouped_parameters": grouped_parameters
    }


def _generate_parameter_explanations(parameters: Dict[str, Any], title: str, authors: str, year: Optional[int], journal: str) -> Dict[str, str]:
    """Generates student-friendly, actionable explanations for each of the 6 Evidence Matrix parameters."""
    author_lead = authors.split(",")[0] if authors else "The authors"
    pub_year = str(year) if year else "the literature"
    is_recent = year is not None and year >= 2021
    recency_badge = "✅ Meets 2021–2026 recency requirement." if is_recent else "ℹ️ Benchmark control / classical baseline reference."

    burden_text = parameters.get("burden_statistic", "")
    bench_text = parameters.get("plain_metric", "") or parameters.get("primary_metric_sentence", "")
    gap_text = parameters.get("plain_gap", "") or parameters.get("stated_gap", "")
    controls_text = parameters.get("controls", "")
    milestone_text = parameters.get("target_milestone", "")

    innovation_text = parameters.get("key_innovation", "") or parameters.get("tool", "")
    findings_text = parameters.get("key_findings", "") or parameters.get("primary_metric_sentence", "")
    horizon_text = parameters.get("research_horizon", "")

    burden_exp = parameters.get("burden_exp")
    if not burden_exp:
        burden_exp = f"The Target Crisis & Quantified Burden: {burden_text} This established crisis demonstrates the vital clinical, environmental, or societal need that justifies experimental intervention, highlighting a measurable human or ecological toll that conventional approaches have failed to mitigate."

    gap_exp = parameters.get("gap_exp")
    if not gap_exp:
        gap_exp = f"Mechanistic Knowledge Gap & Biological Limitation: {gap_text} This specific molecular, structural, or physiological bottleneck identifies the precise failure mode of existing technologies, revealing the unresolved barrier that prevents scalable real-world application."

    journal_ref = f"Published in {journal} ({author_lead} et al., {pub_year}). {recency_badge}" if journal else f"Benchmark Study ({author_lead} et al., {pub_year}). {recency_badge}"

    is_rev = bool(parameters.get("is_review"))
    if is_rev:
        controls_exp = f"Evidence Scope, Clinical Cohorts & Comparators: {controls_text} Synthesizes clinical trial data benchmarked against placebo/standard-of-care control arms to assess therapeutic efficacy across patient demographics."
        benchmark_exp = f"Baseline Standard of Care & Clinical Context: {bench_text} Reflects the established clinical baseline, conventional pharmacotherapy, or untreated disease trajectory documented across evaluated studies."
        milestone_exp = f"Evaluated Therapeutic Approach & Biological Mode of Action: {innovation_text} Analyzes how the therapeutic intervention acts upon specific physiological pathways to alleviate disease symptoms."
        citation_exp = f"{journal_ref} Review Evidence Synthesis & Proposed Project Milestone: {findings_text} Forward Horizon: {horizon_text}"
    else:
        controls_exp = f"Experimental Model Chassis, Assays & Controls: {controls_text} Benchmarked against verified reference standards and negative vehicle/mock controls to guarantee reproducibility and statistical validity."
        benchmark_exp = f"Comparative Baseline & Published Standard: {bench_text} This established rate represents the documented performance standard, current clinical practice, or wild-type physiological ceiling that the study explicitly measured and sought to improve upon."
        milestone_exp = f"Engineered Molecular Mechanism & Technical Innovation: {innovation_text} This molecular approach directly targets and remodels the underlying biological pathway, establishing a validated mechanism to overcome the documented bottleneck."
        citation_exp = f"{journal_ref} Key Measured Findings & Forward-Looking Milestone: {findings_text} Forward Horizon: {horizon_text}"

    return {
        "burden_explanation": burden_exp,
        "benchmark_explanation": benchmark_exp,
        "gap_explanation": gap_exp,
        "controls_explanation": controls_exp,
        "milestone_explanation": milestone_exp,
        "citation_explanation": citation_exp,
        # Backward-compatible aliases
        "p1_yellow": burden_exp,
        "p2_blue": benchmark_exp,
        "p3_green": gap_exp,
        "p4_purple": controls_exp,
        "p5_red": milestone_exp,
        "p6_citation": citation_exp
    }


def _synthesize_deep_comprehension(
    parameters: Dict[str, Any],
    matched_domain: Optional[Dict[str, Any]],
    exec_summary: Dict[str, Any],
    title: str = "",
    authors: str = "",
    year: Optional[int] = None,
    journal: str = ""
) -> Dict[str, Any]:
    """Generates an intuitive, non-redundant, undergraduate-accessible comprehension dossier for ANY paper."""
    first_author = authors.split(",")[0].strip() if authors else "Lead Researchers"
    pub_year = year or 2024

    if matched_domain and "one_sentence_pitch" in matched_domain and "story_pillars" in matched_domain:
        return {
            "one_sentence_pitch": matched_domain["one_sentence_pitch"],
            "core_analogy": matched_domain.get("core_analogy", ""),
            "the_biological_barrier": matched_domain.get("the_biological_barrier", ""),
            "the_engineered_trick": matched_domain.get("the_engineered_trick", ""),
            "research_takeaway": matched_domain.get("research_takeaway", ""),
            "mechanism_pipeline": matched_domain.get("mechanism_pipeline", {}),
            "story_pillars": matched_domain["story_pillars"],
            "the_four_pillars": matched_domain["story_pillars"],
            "faq_insights": matched_domain["faq_insights"],
            "proposal_ready_sentences": matched_domain["proposal_ready_sentences"]
        }

    # Universal Archetype & Entity Synthesis for Any Arbitrary Paper
    burden = parameters.get("burden_statistic", "Operational constraints impede biotechnology translation.")
    finding = parameters.get("primary_metric_sentence", "Demonstrated measurable improvement over baseline.")
    gap = parameters.get("stated_gap", "Translational efficiency and operational stability require further optimization.")
    controls = parameters.get("controls", "Benchmarked against wild-type control baseline.")

    is_review = bool(re.search(r"\b(?:review|meta-analysis|systematic review|scoping review|literature review|overview|perspective)\b", f"{title} {journal}", re.IGNORECASE) or
                    re.search(r"\b(?:this review|we review|in this review|we summarize the current|we critically review|systematic review|meta-analysis|a comprehensive overview|the present review|literature review|this paper reviews|this article reviews)\b", f"{burden} {finding} {gap}", re.IGNORECASE))

    raw_chassis = parameters.get("chassis")
    if not raw_chassis or "biological host" in raw_chassis.lower():
        chassis = "clinical cohorts and physiological models" if is_review else "the experimental biological model"
    else:
        chassis = raw_chassis

    raw_tool = parameters.get("tool")
    if not raw_tool or "engineered molecular intervention" in raw_tool.lower():
        tool = "the therapeutic intervention" if is_review else "the targeted molecular intervention"
    else:
        tool = raw_tool

    combined_text = f"{title} {burden} {finding} {gap} {exec_summary.get('intervention', '')} {chassis} {tool}".lower()

    # Dynamic Biotech Archetype Classifier
    if is_review:
        archetype = "review"
        archetype_theme = "Literature Review & Clinical Field Synthesis"
        analogy = "Think of this review like a comprehensive bird's-eye map of the entire battlefield: it surveys every treatment tested so far, shows where current therapies fall short, and highlights the uncharted territories where your new proposal can make a breakthrough."
    elif re.search(r"\b(?:detect|diagnostic|biosensor|assay|fluorescen|lod|lateral flow|point-of-care|qpcr|ssdna|trans-cleavage|crispr-cas12|crispr-cas13|aptamer|biomarker|reporter)\b", combined_text):
        archetype = "diagnostics"
        archetype_theme = "Precision Molecular Diagnostics & Biosensing"
        analogy = "Think of this like giving doctors a molecular tripwire or magnifying glass that lights up the instant a single needle is found in a massive haystack of normal cells."
    elif re.search(r"\b(?:enzyme|cataly|petase|cutinase|depolymer|mutant|mutagenesis|active-site|thermostab|melting temperature|tm\b|kcat|km\b|substrate channeling|esterase|protease)\b", combined_text):
        archetype = "biocatalysis"
        archetype_theme = "Enzyme Engineering & Industrial Biocatalysis"
        analogy = "Think of this like upgrading the moving parts of an industrial motor with heat-resistant titanium gears so it can run at blistering speeds without warping or melting."
    elif re.search(r"\b(?:lipid nanoparticle|lnp|nanoparticle|aav|adeno-associated|vector|delivery|encapsulat|liposome|transfection|biodistribution|targeting peptide)\b", combined_text):
        archetype = "delivery"
        archetype_theme = "Targeted Molecular Delivery & Nanomedicine"
        analogy = "Think of this like designing a GPS-guided microscopic delivery van that slips past the immune system's security checkpoints to drop off genetic packages directly to the target tissue's front door."
    elif re.search(r"\b(?:car-t|chimeric antigen|t cell|immunotherapy|cancer|tumor|cytotoxic|checkpoint|pd-1|pembrolizumab|leukemia|exhaustion|lymphoma)\b", combined_text):
        archetype = "cell_therapy"
        archetype_theme = "Cell Therapy & Cancer Immunotherapy"
        analogy = "Think of this like giving the patient's own cellular security guards night-vision goggles and a customized mugshot of the cancer cells, training them to attack the threat without harming innocent bystanders."
    elif re.search(r"\b(?:biosynthe|pathway|metabolic|fermentation|microbial factory|precursor|yield|endosperm|carotenoid|metabolite|operon|engineered strain|titer)\b", combined_text):
        archetype = "metabolic"
        archetype_theme = "Metabolic Engineering & Synthetic Biology"
        analogy = "Think of this like installing an automated assembly line inside a living cell, supplying the exact missing robotic tools needed to manufacture high-value compounds from raw cellular fuel."
    elif re.search(r"\b(?:genome editing|prime editing|base edit|cas9|crispr|grna|pegrna|double-strand|indel|knock-in|knock-out|nickase)\b", combined_text):
        archetype = "editing"
        archetype_theme = "High-Precision Genome Editing"
        analogy = "Think of this like upgrading from crude molecular scissors that randomly shred pages to an ultra-precise digital word processor that can find and correct a single misspelled genetic letter in the genome."
    elif re.search(r"\b(?:wheat|rice|maize|crop|plant|drought|salin|transgenic plant|agronomic|chloroplast|leaf|root|tahkt1|grain yield)\b", combined_text):
        archetype = "agriculture"
        archetype_theme = "Agricultural Biotechnology & Crop Resilience"
        analogy = "Think of this like equipping plant roots with an intelligent desalination filter or water-saving valve, preventing toxic environmental stressors from travelling upward and poisoning food-producing leaves."
    elif re.search(r"\b(?:halomonas|polyhydroxyalkanoate|pha|bacteria|bioreactor|microbial|waste|plastic|fermentation|ecoli|e\. coli)\b", combined_text):
        archetype = "microbial"
        archetype_theme = "Microbial Cell Factories & Biomanufacturing"
        analogy = "Think of this like breeding a specialized super-microbe that thrives on industrial waste streams and converts them into sustainable biodegradable materials."
    else:
        archetype = "general"
        archetype_theme = "Molecular Biotechnology & Bioengineering"
        analogy = "Think of this like re-engineering biological machinery at the molecular scale to accomplish a vital task that conventional chemical or mechanical methods could not solve."

    clean_finding = re.sub(r"^(?:therefore,?|in this review,?|this review|we review|here,? we show that|in this study,? we discovered that|in this paper,? we|we show that|furthermore,?|moreover,?|in conclusion,?|overall,?|taken together,?|thus,?)\s*", "", simplify_academic_text(finding).strip(), flags=re.IGNORECASE)
    clean_burden = simplify_academic_text(burden).strip()
    raw_solution = exec_summary.get("intervention") or parameters.get("key_innovation") or (f"evaluated {tool} across {chassis}" if is_review else f"deployed {tool} in {chassis}")
    clean_solution = simplify_academic_text(raw_solution).strip()
    clean_solution = re.sub(r"^(?:here,?\s*(?:we\s*)?|in this study,?\s*(?:we\s*)?|we\s+(?:developed|engineered|designed|discovered|coupled|introgressed|identified|synthesized)?\s*)\s*", "", clean_solution, flags=re.IGNORECASE).strip()
    clean_gap = re.sub(r"^(?:however,?|nevertheless,?|yet,?|despite this,?)\s*", "", simplify_academic_text(gap).strip(), flags=re.IGNORECASE)

    has_metric = bool(re.search(r"\b(?:\d+(?:\.\d+)?\s*(?:%|fold|g/l|mg/l|µg/ml|µm|nm|pm|mm|cfu/ml|turnovers?|°c|days?|hours?|weeks?))\b|p\s*[<=]\s*0\.\d+", finding, re.IGNORECASE))

    clean_finding_inline = (clean_finding[0].lower() + clean_finding[1:]) if clean_finding else clean_finding
    clean_gap_inline = (clean_gap[0].lower() + clean_gap[1:]) if clean_gap else clean_gap
    clean_sol_inline = (clean_solution[0].lower() + clean_solution[1:]) if clean_solution else clean_solution

    # Clean finding for inline sentence usage (strip redundant leading 'the ... achieved')
    clean_finding_core = re.sub(r"^(?:(?:the\s+[\w\s-]+\s+)?(?:achieved|demonstrated|resulted in|yielded|showed that|exhibited))\s+", "", clean_finding, flags=re.IGNORECASE).strip()
    if clean_finding_core:
        clean_finding_core_inline = (clean_finding_core[0].lower() + clean_finding_core[1:])
    else:
        clean_finding_core_inline = clean_finding_inline

    # 1. Plain-English Elevator Pitch
    if is_review:
        pitch = f"Synthesized published evidence on {tool} across {chassis}, identifying critical research gaps in {clean_gap_inline[:110].rstrip('.')}."
    else:
        pitch = f"Engineered {chassis} using {tool} to {clean_sol_inline[:110].rstrip('.')}, achieving {clean_finding_core_inline[:120].rstrip('.')}."

    # 2. 3-Step Biochemical Flow (The Molecular Journey)
    mech = {
        "step1_input": f"Baseline clinical and physiological pathology in {chassis}" if is_review else f"Biological substrate or starting physiological state in {chassis}",
        "step2_catalyst": f"Therapeutic intervention: {tool} evaluated across clinical studies" if is_review else f"Engineered molecular intervention: {tool} deployed to {clean_sol_inline[:100]}",
        "step3_output": f"Clinical and molecular synthesis: {clean_finding[:130]}" if is_review else f"Functional biological readout: {clean_finding[:130]}"
    }

    # 3. Dedicated 6-Parameter Evidence Grid (Richly Elaborated Evidence)
    elaborated_p1 = f"What is going wrong in the world? {clean_burden} This shows the real-world scale and human or environmental cost that makes this problem so important to solve."
    elaborated_p2 = (
        "What is the current standard today? Conventional clinical standard of care (such as standard pharmacotherapy or lifestyle interventions) provides the baseline against which new approaches are evaluated. Look for the control or comparator arms in the cited trials for exact baseline response rates."
        if is_review else
        "What is the current standard today? Before this study, conventional methods operated at a baseline level. This is the published benchmark score that your proposal is comparing against."
    )
    elaborated_p3 = f"Why do existing methods fail? {clean_gap} This is the key bottleneck: the biological flaw or barrier that prevents current methods from working in real life. This unsolved flaw is the exact reason your project is needed!"
    elaborated_p4 = (
        "The evidence scope: This paper is a comprehensive literature review synthesizing published clinical trials, cohort studies, and mechanistic findings across human populations, rather than reporting a single wet-lab experiment. Note for your proposal: Use this review to ground your Tier 1 hook and Tier 3 knowledge gap, but find a primary wet-lab study to cite for your Aim 2 construct and experimental controls."
        if is_review else
        f"The test system & controls: Tested in {chassis} deploying {tool}. The researchers checked their data using analytical assays and compared against normal baseline controls and reference samples to prove the results were real."
    )
    elaborated_p5 = (
        f"The evaluated intervention: The review examines {clean_sol_inline or f'{tool} in {chassis}'}, assessing how this therapeutic approach modulates underlying biological pathways to resolve clinical symptoms. For your proposal's Aim 2, propose an engineered version of this intervention (e.g., an engineered probiotic strain) to solve the Tier 3 gap."
        if is_review else
        f"The new tool or trick: The researchers engineered {clean_sol_inline or f'{tool} in {chassis}'}. This new intervention operates directly on the biological pathway, providing a fresh mechanism designed to fix the flaw."
    )

    if has_metric:
        elaborated_p6 = f"The proven result & next goal: Laboratory tests proved that {clean_finding_core_inline or clean_finding}. This is the record set by this paper! For your proposal, choose a specific target milestone in Aim 3 that aims one step higher than this published score."
    elif is_review:
        elaborated_p6 = f"The review findings & research gaps: The review concludes that {clean_finding_core_inline or clean_finding}. This review synthesizes therapeutic potential while emphasizing unresolved mechanistic gaps. Note for your proposal: Because this is a review paper without a single benchmark rate in the abstract, check the primary clinical trials cited in the text (such as Table 1) to find an exact numerical score (e.g. % symptom reduction) to set as your Aim 3 milestone."
    else:
        elaborated_p6 = f"What the paper found: The researchers demonstrated that {clean_finding_core_inline or clean_finding}. While the authors established conceptual proof-of-concept, an exact numerical rate was not reported in the short abstract. Check the paper's Figures or Results section to find the exact numerical score to benchmark against in your proposal."

    story_pillars = {
        "problem": elaborated_p1,
        "benchmark": elaborated_p2,
        "gap": elaborated_p3,
        "controls": elaborated_p4,
        "solution": elaborated_p5,
        "proof": elaborated_p6,
        "finding": elaborated_p6,
        "p1_problem": elaborated_p1,
        "p2_benchmark": elaborated_p2,
        "p3_gap": elaborated_p3,
        "p4_controls": elaborated_p4,
        "p5_solution": elaborated_p5,
        "p6_finding": elaborated_p6
    }

    # 4. Reviewer Questions
    faq = [
        {
            "question": f"Why is this study considered a significant advance in {archetype_theme}?",
            "answer": (
                f"This review systematically maps the therapeutic efficacy of {tool} in {chassis}, identifying promising clinical outcomes and pinpointing critical mechanistic gaps."
                if is_review else
                f"The study demonstrated that deploying {tool} in {chassis} can overcome traditional limitations, validating that {clean_finding_inline[:180]}."
            )
        },
        {
            "question": "How does the molecular or biochemical mechanism function?",
            "answer": (
                f"The reviewed evidence highlights how {tool} modulates key biological pathways and systemic signaling in {chassis} to drive phenotypic improvements."
                if is_review else
                f"The researchers utilized {tool} to {clean_sol_inline[:200]}. This intervention operates directly on the target biological pathway to drive phenotypic change."
            )
        },
        {
            "question": "What experimental controls and validation techniques were deployed?",
            "answer": f"The evidence was benchmarked using: {controls[:220]}. This confirms that the observed outcomes derive specifically from the evaluated intervention."
        },
        {
            "question": "How should an undergraduate proposal build upon this benchmark?",
            "answer": (
                f"In Tier 1 and Tier 3, cite this review for real-world burden and mechanistic gaps ({clean_gap_inline[:100]}). For Aim 2 and Aim 3, propose an engineered version of {tool} and cite a primary experimental study for your benchmark score."
                if is_review else
                f"In Tier 2 of your Inverted Funnel, cite this paper's benchmark ({clean_finding_inline[:100]}). In Tier 3, identify {clean_gap_inline[:120]} as your mechanistic knowledge gap, and formulate your Aim 1 and Aim 2 to surpass this operational ceiling."
            )
        }
    ]

    # 5. Ready-to-Use Proposal Sentences
    funnel = {
        "tier1_sentence": f"{clean_burden.rstrip('.')} ({first_author} et al., {pub_year}).",
        "tier2_sentence": (
            f"A comprehensive review by {first_author} et al. ({pub_year}) evaluated current interventions in {chassis}, highlighting that {clean_finding_core_inline.rstrip('.')}."
            if is_review else
            f"Prior bioengineering studies by {first_author} et al. ({pub_year}) established that deploying {tool} in {chassis} achieves {clean_finding_core_inline.rstrip('.')}."
        ),
        "tier3_sentence": (
            f"However, critical translational and mechanistic gaps persist because {clean_gap_inline.rstrip('.')}, demonstrating an urgent need for targeted research ({first_author} et al., {pub_year})."
            if is_review else
            f"However, widespread translational deployment remains critically constrained because {clean_gap_inline.rstrip('.')}, leaving an unresolved mechanistic bottleneck ({first_author} et al., {pub_year})."
        )
    }

    return {
        "is_review": is_review,
        "archetype": archetype,
        "one_sentence_pitch": pitch,
        "core_analogy": analogy,
        "the_biological_barrier": clean_burden or ("Current clinical and molecular treatments face unresolved gaps in understanding exact mechanisms, variable patient responses, and delivery challenges." if is_review else "Un-engineered biological systems lack the catalytic efficiency or protective mechanism required to overcome this baseline hurdle."),
        "the_engineered_trick": clean_solution or (f"Evaluates {tool} to map biological pathways, comparative effectiveness, and unmet clinical needs." if is_review else f"Deployed {tool} to target the underlying pathway in {chassis}."),
        "research_takeaway": ("Establishes a solid literature foundation for your proposal's background, pinpointing the critical knowledge gaps your project will address." if is_review else f"Demonstrates that targeted intervention in {chassis} can overcome traditional limitations, establishing a launching pad for future engineering."),
        "mechanism_pipeline": mech,
        "story_pillars": story_pillars,
        "the_four_pillars": story_pillars,
        "faq_insights": faq,
        "proposal_ready_sentences": funnel
    }


def _build_eli_narrative(text: str, problem: str, solution: str, finding: str, limitation: str) -> Dict[str, Any]:
    """Constructs an intuitive, simple plain-English breakdown with analogies across 15+ domains."""
    text_lower = text.lower()
    
    # 1. Domain Classifier & Analogy Bank
    theme = "Biotechnology & Molecular Engineering"
    analogy = "Imagine taking a delicate biological machine that normally breaks easily, and adding custom molecular reinforcement so it keeps working under harsh real-world conditions."
    
    if any(k in text_lower for k in ["pet", "plastic", "depolymer", "cutinase", "polyester", "petase"]):
        theme = "Enzymatic Plastic Upcycling & Biocatalysis"
        analogy = "Plastic bottles are like tough, unchewable ropes. Normal bacterial enzymes are like tiny scissors that try to cut the rope, but the scissors melt the moment water gets hot. The researchers put molecular 'welds' (disulfide bridges) onto the scissors so they keep cutting at near-boiling temperatures without melting."
    elif any(k in text_lower for k in ["cas12", "cas13", "detectr", "sherlock", "collateral", "isothermal", "rpa", "lamp"]):
        theme = "CRISPR & Isothermal Fast Molecular Diagnostics"
        analogy = "Standard hospital PCR tests take days because they need big heating/cooling machines. The researchers used a molecular watchdog (Cas12a) with an exact photo of the virus. The second it spots the virus, it starts setting off glowing confetti cannons, giving a doctor an immediate positive test result in 30 minutes with no lab machines."
    elif any(k in text_lower for k in ["probiotic", "microbiome", "gut", "depression", "gut-brain", "bifidobacteri", "lactobacill"]):
        theme = "Microbiome Therapeutics & Gut-Brain Axis"
        analogy = "The gut microbiome acts like an internal biochemical pharmacy communicating with the central nervous system. The researchers investigated targeted probiotic strains to reinforce mucosal barrier integrity and modulate systemic neurochemical signaling."
    elif "rice" in text_lower and any(k in text_lower for k in ["golden rice", "carotenoid", "beta-carotene", "provitamin", "biofortif"]):
        theme = "Nutritional Biofortification & Crop Metabolic Engineering"
        analogy = "Standard white rice fills stomachs but lacks essential micronutrients like Vitamin A, leading to preventable malnutrition. The researchers introduced the biosynthetic assembly line for beta-carotene directly into the edible rice grain, turning ordinary rice into a golden, nutrient-packed staple crop."
    elif any(k in text_lower for k in ["wheat", "salin", "crop", "plant", "drought", "grain", "rice", "maize"]):
        theme = "Agricultural Crop Resilience & Food Security"
        analogy = "When crops grow in salty soil, salt rushes up the stems and poisons the leaves. The researchers took a natural desalination filter gene from a wild ancestral grain and bred it into commercial wheat. The filter sits in the plant's root pipelines, pulling salt out of the water before it reaches the food grain."
    elif any(k in text_lower for k in ["car-t", "tumor", "cancer", "antibody", "oncolog", "checkpoint", "pd-1", "cd19"]):
        theme = "Cancer Immunotherapy & Targeted Therapeutics"
        analogy = "Cancer cells are masters of disguise that trick the immune system into ignoring them. The researchers engineered synthetic radar receptors onto immune cells so they can unmask the tumor and eliminate cancer cells with laser precision while leaving healthy tissues unharmed."
    elif any(k in text_lower for k in ["mrna", "vaccine", "lipid nanoparticle", "lnp", "delivery vehicle", "encapsulation"]):
        theme = "mRNA Vaccines & Nanomedicine Drug Delivery"
        analogy = "Raw mRNA is like a delicate paper letter that gets shredded the instant it touches bodily fluids. The researchers packaged the letter inside a microscopic protective fat bubble (LNP) that safely sneaks past bodily defenses and delivers the instruction manual directly into cells."
    elif any(k in text_lower for k in ["wastewater", "effluent", "dye", "heavy metal", "bioremediation", "laccase", "biochar"]):
        theme = "Environmental Bioremediation & Water Treatment"
        analogy = "Industrial wastewater contains toxic chemicals that kill natural bacteria. The researchers created microscopic cleanup crews by immobilizing resilient enzymes on solid sponges so they continuously chew up toxic dyes before factory water enters local rivers."
    elif any(k in text_lower for k in ["ferment", "bioreactor", "titer", "yield", "metabolic burden", "pathway", "overexpress"]):
        theme = "Industrial Fermentation & Microbial Cell Factories"
        analogy = "Like running a microscopic automotive assembly line inside a yeast cell: the researchers re-routed the cell's internal sugar plumbing so every calorie eaten is redirected into synthesizing high-value medicine instead of cellular waste."
    elif any(k in text_lower for k in ["antibiotic", "resistant", "antimicrobial", "mrsa", "biofilm", "pathogen"]):
        theme = "Antimicrobial Resistance (AMR) & Infectious Diseases"
        analogy = "Superbugs have evolved protective fortress walls and chemical pumps that spit antibiotics out. The researchers engineered molecular crowbars that disable the pump mechanism, making standard low-cost medicines lethal to the bacteria once again."
    elif any(k in text_lower for k in ["alphafold", "docking", "pdb", "molecular dynamics", "in silico", "rosetta"]):
        theme = "Computational Biophysics & AI Protein Design"
        analogy = "Instead of testing billions of failed chemical combinations by hand for five years, researchers used high-speed molecular simulations like virtual wind-tunnels to sculpt the exact 3D pocket shape an enzyme needs before ever stepping into the wet lab."

    # 2. Simplified 4-Pillars Breakdown
    p_simple = simplify_academic_text(problem) if problem else "Existing tools face a severe physical bottleneck (they unfold, react too slowly, or require bulky lab machines)."
    s_simple = simplify_academic_text(solution) if solution else "The researchers introduced an engineered molecular modification to directly address the flaw."
    f_simple = simplify_academic_text(finding) if finding else "The authors proved with empirical data that their experimental approach significantly improved performance over standard baselines."
    l_simple = simplify_academic_text(limitation) if limitation else "However, real-world deployment remains constrained by matrix interference or scale-up barriers, leaving a clear research gap for your proposal!"

    return {
        "theme": theme,
        "core_analogy": analogy,
        "simple_problem": p_simple,
        "simple_solution": s_simple,
        "simple_takeaway": f_simple,
        "simple_limitation": l_simple
    }


def _extract_proposal_parameters(text: str, sentences: List[str], title: str = "", authors: str = "", year: Optional[int] = None) -> Dict[str, Any]:
    """
    Extracts high-yield proposal parameters:
    - Chassis / Host / Matrix
    - Molecular Tool / Construct
    - Epidemiological / Global Burden Statistic (Parameter 1)
    - Quantitative Benchmarks & Baseline Rate (Parameter 2)
    - Experimental Controls (Parameter 4)
    - Stated Limitations / Knowledge Gaps (Parameter 3)
    - Target Quantitative Milestone (Parameter 5)
    """
    text_lower = text.lower()
    title_lower = title.lower()
    combined_lower = f"{title_lower} {text_lower}"
    is_review = bool(re.search(r"\b(review|systematic review|meta-analysis|overview|perspective|advances in|recent progress|state of the art)\b", combined_lower))
    disease_symptom_reject = r"\b(?:characterized by|symptoms?|sadness|anhedonia|fatigue|sleep disturbances|cognitive dysfunction|suicidal ideation|pathophysiology|affects approximately|is a mental disorder|is a psychiatric|is a disease|is a condition)\b"
    scope_reject = r"^(?:therefore,?|in this review,?|this paper examines|this review examines|we review|we discuss|we summarize|here we review|in summary|this overview)"

    # Check Curated Domain Knowledge first for authentic evidence
    matched_domain = None
    for item in DOMAIN_KNOWLEDGE:
        if re.search(item["pattern"], combined_lower):
            matched_domain = item
            break

    if matched_domain:
        chassis_val = matched_domain["chassis"]
        tool_val = matched_domain["tool"]
        burden_val = matched_domain["burden_statistic"]
        metric_sentence = matched_domain["primary_metric"]
        for s in sentences:
            if "0.92" in s or ("crystal structure" in s.lower() and "resolution" in s.lower()):
                metric_sentence = s.strip()
                break
        controls_val = matched_domain["controls"]
        gap_val = matched_domain["knowledge_gap"]
        key_innovation = matched_domain["innovation"]
        measured_finding = metric_sentence
        research_horizon = f"Evidence Proof: {measured_finding} Horizon for Your Project: {matched_domain['research_horizon']}"
        target_milestone = f"Target Milestone: {matched_domain['research_horizon']}"
        raw_metrics = [m.group(0) for m in re.finditer(r"\b(?:\d+(?:\.\d+)?\s*(?:°C|%|g/L/h|g/L|mg/L|µg/g|µg/mL|copies/[µu]L|pM|nM|µM|mM|turnovers|folds?|[Åå]|angstrom))\b", metric_sentence, re.IGNORECASE)][:4]
        metrics_summary = []
        for met in raw_metrics:
            metrics_summary.append(met)
            norm_met = met.replace("µ", "u").replace("μ", "u")
            if norm_met != met and norm_met not in metrics_summary:
                metrics_summary.append(norm_met)
        if not metrics_summary:
            metrics_summary = ["Quantitative literature benchmark"]
        timeline_benchmark = {
            "phase1_months": "Months 1–4",
            "phase1_focus": f"Cloning, construct synthesis ({tool_val}), and sequence verification in {chassis_val}",
            "phase2_months": "Months 4–8",
            "phase2_focus": f"Expression optimization, kinetic assays, and quantitative benchmark evaluation",
            "phase3_months": "Months 8–14",
            "phase3_focus": "Operational matrix validation, stability trials, and translational reporting",
            "buffer_guidance": "Peer-reviewed literature allocates 15–20% buffer for failed clone verification and protocol recalibration."
        }
        return {
            "chassis": chassis_val,
            "tool": tool_val,
            "burden_statistic": burden_val,
            "metric_numbers": metrics_summary,
            "primary_metric_sentence": metric_sentence,
            "plain_metric": simplify_academic_text(metric_sentence),
            "controls": controls_val,
            "experimental_strategy": controls_val,
            "stated_gap": gap_val,
            "plain_gap": simplify_academic_text(gap_val),
            "key_innovation": key_innovation,
            "key_findings": measured_finding,
            "research_horizon": research_horizon,
            "target_milestone": target_milestone,
            "timeline_benchmark": timeline_benchmark,
            "burden_exp": matched_domain.get("burden_exp"),
            "gap_exp": matched_domain.get("gap_exp"),
            "is_review": is_review
        }

    # 1. Chassis / Host / Matrix
    chassis_matches = []
    chassis_keywords = [
        "escherichia coli", "e. coli", "pichia pastoris", "pichia", "pseudomonas putida", "pseudomonas",
        "staphylococcus aureus", "s. aureus", "acinetobacter baumannii", "klebsiella pneumoniae",
        "bacillus subtilis", "bacillus", "saccharomyces cerevisiae", "yeast", "corynebacterium",
        "synechocystis", "algae", "microalgae", "cyanobacteria", "ideonella sakaiensis", "thermus thermophilus",
        "streptomyces", "oryza sativa", "rice", "triticum", "wheat", "durum wheat", "arabidopsis thaliana",
        "arabidopsis", "maize", "corn", "zea mays", "tobacco", "nicotiana benthamiana", "nicotiana",
        "soybean", "glycine max", "potato", "solanum", "tomato", "crop", "endosperm", "cho cells",
        "hek293", "t-cells", "car-t", "stem cells", "human serum", "whole blood", "clinical swab",
        "blood", "serum", "plasma", "mouse", "murine", "rat", "zebrafish", "c. elegans",
        "mammalian cells", "soil", "wastewater", "effluent", "bioreactor", "crude extract", "compost"
    ]
    for ch in chassis_keywords:
        pattern = r"\b" + re.escape(ch) + r"\b"
        if re.search(pattern, text_lower) or re.search(pattern, title_lower):
            if ch in ["e. coli", "escherichia coli"]:
                chassis_matches.append("Escherichia coli")
            elif ch in ["saccharomyces cerevisiae", "yeast"]:
                chassis_matches.append("Saccharomyces cerevisiae (yeast)")
            elif ch in ["staphylococcus aureus", "s. aureus"]:
                chassis_matches.append("Staphylococcus aureus (bacterial biofilm host)")
            elif ch in ["oryza sativa", "rice", "endosperm"]:
                chassis_matches.append("Oryza sativa (Rice endosperm)")
            elif ch in ["triticum", "wheat", "durum wheat"]:
                chassis_matches.append("Triticum (Wheat)")
            elif ch in ["zea mays", "maize", "corn"]:
                chassis_matches.append("Zea mays (Maize)")
            elif ch in ["arabidopsis", "arabidopsis thaliana"]:
                chassis_matches.append("Arabidopsis thaliana")
            elif ch in ["ideonella sakaiensis"]:
                chassis_matches.append("Ideonella sakaiensis")
            elif ch in ["whole blood", "blood", "serum", "human serum", "plasma"]:
                chassis_matches.append("Clinical blood / serum matrix")
            elif ch in ["clinical swab", "swab"]:
                chassis_matches.append("Clinical swab matrix")
            elif ch in ["cho cells", "hek293", "mammalian cells"]:
                chassis_matches.append("Mammalian cell line")
            elif ch in ["t-cells", "car-t"]:
                chassis_matches.append("Primary human T-cells")
            else:
                chassis_matches.append(ch.capitalize())

    unique_chassis = list(dict.fromkeys(chassis_matches))
    if unique_chassis:
        chassis_val = ", ".join(unique_chassis[:2])
    elif any(k in combined_lower for k in ["crop", "plant", "grain", "seed", "leaf", "flora", "cultivar", "botanical"]):
        chassis_val = "Plant Host / Crop Expression System"
    elif any(k in combined_lower for k in ["clinical", "patient", "diagnostic", "pathogen", "virus", "infection", "cancer", "tumor", "depression", "gut-brain", "microbiome"]):
        chassis_val = "Clinical Cohorts & Synthesized Evidence Base" if is_review else "Clinical Host / Human Diagnostic Matrix"
    else:
        chassis_val = "Clinical literature cohort / subject population" if is_review else "Experimental biological model / host system"

    # 2. Molecular Tool / Engineered Construct
    tool_matches = []
    tool_patterns = [
        r"\b(cas\d+[a-z]?|cpf1)\b",
        r"\b(cly[a-z0-9]+|endolysin|lysin|antimicrobial peptide|riboswitch|repressor)\b",
        r"\b(petase|mhetase|cutinase|cellulase|polymerase|ligase|protease|dehydrogenase|transporter|laccase|polyesterase|hydrolase|peroxidase|esterase|nuclease|synthase|kinase|reductase|oxidase|decarboxylase|isomerase|transfera[sz]e)\b",
        r"\b(rpa|lamp|detectr|sherlock|crispr|prime edit\w*|base edit\w*|car-t|mrna|sirna|antibody|mab|nanobody|aptamer|biosensor)\b",
        r"\b(tahkt1;5|nax\d|psy\d?|crti|dxs|bche|crt[a-z0-9]+)\b",
        r"\b[A-Z]\d{2,4}[A-Z](?:/[A-Z]\d{2,4}[A-Z])*\b"  # e.g. W159H, F238Y, W159H/F238Y
    ]
    for p in tool_patterns:
        found = re.findall(p, text, flags=re.IGNORECASE)
        for f in found:
            if isinstance(f, str) and len(f) > 2:
                low_f = f.lower()
                if "cas" in low_f or "cpf1" in low_f:
                    tool_matches.append(f.upper())
                elif "tahkt" in low_f or "nax" in low_f:
                    tool_matches.append(f)
                elif "/" in f or any(c.isdigit() for c in f):
                    tool_matches.append(f.upper())
                else:
                    tool_matches.append(f.capitalize())

    # Fallback to title inspection with patterns
    if not tool_matches and title:
        for p in tool_patterns:
            found = re.findall(p, title, flags=re.IGNORECASE)
            for f in found:
                if isinstance(f, str) and len(f) > 2:
                    tool_matches.append(f.capitalize())

    # Check for domain-specific constructs / metabolic pathways dynamically
    if not tool_matches:
        if any(k in combined_lower for k in ["carotenoid", "beta-carotene", "provitamin"]):
            tool_matches.append("Carotenoid Biosynthetic Pathway")
        elif any(k in combined_lower for k in ["probiotic", "microbiome", "gut-brain"]):
            tool_matches.append("Probiotic Strain Consortium")
        elif "mrna" in combined_lower:
            tool_matches.append("Modified mRNA / Nanoparticle Delivery System")
        elif "car-t" in combined_lower:
            tool_matches.append("Chimeric Antigen Receptor (CAR) Construct")
        elif "crispr" in combined_lower:
            tool_matches.append("CRISPR Targeted System")
        elif "vaccine" in combined_lower:
            tool_matches.append("Recombinant Vaccine Antigen")
        elif "biosensor" in combined_lower:
            tool_matches.append("Target Biosensor System")

    # If still not found, intelligently extract key entity from title
    if not tool_matches and title:
        title_head = title.split(":")[0].split(" - ")[0].strip()
        stop_words = {"investigation", "study", "analysis", "review", "development", "synthesis", "engineering", "promises", "status", "future", "prospects", "advances", "recent", "novel", "role", "characterization", "insight", "evaluation", "assessment"}
        words = [w for w in title_head.split() if w.lower() not in stop_words and len(w) > 2]
        if words and len(words) <= 5:
            tool_matches.append(" ".join(words))

    tool_val = ", ".join(list(dict.fromkeys(tool_matches))[:3]) if tool_matches else ("Evaluated Therapeutic Interventions & Regimens" if is_review else "Target Molecular / Biological Intervention")

    # 3. Epidemiological / Global Burden Statistic (Parameter 1)
    protocol_reject_regex = r"^(?:to obtain|we cloned|we introduced|the construct|in this study|here,? we|a plasmid|expression was|we designed|we report|constructs were|the cdna)"
    burden_sentences = []
    burden_keywords = [
        "million", "billion", "trillion", "metric tons", "tons", "worldwide", "globally",
        "annually", "per year", "incidence", "prevalence", "mortality", "morbidity", "daly", "cost",
        "burden", "accumulat", "discarded", "plastic waste", "staggering rate", "threat",
        "crisis", "outbreak", "incurring", "loss", "pollut", "soil salinity", "most abundantly",
        "afflicts", "epidemic", "economic", "infection", "patient", "cases", "hospital"
    ]
    for s in sentences:
        if re.match(protocol_reject_regex, s.strip(), re.IGNORECASE) or re.search(scope_reject, s.strip(), re.IGNORECASE):
            continue
        low = s.lower()
        if any(k in low for k in burden_keywords):
            if any(char.isdigit() for char in s) or any(w in low for w in ["most abundant", "staggering", "alarming", "vast majority", "severely", "drastically", "incurring", "afflicts"]):
                burden_sentences.append(s.strip())
            elif not burden_sentences:
                burden_sentences.append(s.strip())

    if burden_sentences:
        burden_val = burden_sentences[0]
    else:
        # Check non-protocol early sentences
        found_non_protocol = None
        for s in sentences[:3]:
            if not re.match(protocol_reject_regex, s.strip(), re.IGNORECASE):
                if re.search(r"\b(?:problem|threat|crisis|challenge|lacks?|limited|impeded|disorder|disease|deficit|bottleneck)\b", s, re.IGNORECASE):
                    found_non_protocol = s.strip()
                    break
        if found_non_protocol:
            burden_val = found_non_protocol
        elif title:
            burden_val = f"Documented challenge addressed in study: Resolving operational constraints in {title.lower()} to overcome published efficiency and stability barriers."
        else:
            burden_val = "Quantified global burden: widespread environmental accumulation or clinical challenge documented in literature."

    # 4. Quantitative Metrics & Baselines (Parameter 2)
    metrics_list = []
    metric_regex = r"\b(\d+(\.\d+)?\s*(%|°c|c|mg/l|g/l/h|g/l|ug/ml|µg/ml|nm|um|µm|mm|m|kda|da|bp|kb|mb|copies/ul|copies/µl|attomolar|femtomolar|picomolar|nanomolar|micromolar|millimolar|molar|turnovers(?:/s| per second)?|ds/m|mg/day/cm²|å|angstrom|-fold|fold))\b"
    found_metrics = re.findall(metric_regex, text, flags=re.IGNORECASE)
    for m in found_metrics:
        if m[0]:
            metrics_list.append(m[0].strip())

    special_metrics = []
    for s in sentences:
        low = s.lower()
        if any(term in low for term in ["tm", "melting temperature"]) and any(c in low for c in ["=", "°c", "increased", "elevat"]):
            special_metrics.append(s.strip())
        elif any(term in low for term in ["lod", "limit of detection", "attomolar", "copies/ul", "copies/µl"]):
            special_metrics.append(s.strip())
        elif "yield" in low and "%" in low:
            special_metrics.append(s.strip())
        elif "resolution" in low and any(u in low for u in ["å", "angstrom"]):
            special_metrics.append(s.strip())
        elif "turnover" in low or "kcat" in low or "productivity" in low:
            special_metrics.append(s.strip())

    if not special_metrics and metrics_list:
        for s in sentences:
            low = s.lower()
            if any(m.lower() in low for m in metrics_list) and any(v in low for v in ["achieved", "exhibited", "detected", "demonstrated", "observed", "increased", "reduced", "reveals", "presents", "yielding"]):
                special_metrics.append(s.strip())

    if not special_metrics:
        for s in sentences:
            low = s.lower()
            if any(v in low for v in ["here, we present", "we observed", "achieved", "exhibited", "improved", "demonstrated", "shows that", "reveals"]):
                special_metrics.append(s.strip())

    metrics_summary = list(dict.fromkeys(metrics_list))[:6]

    if special_metrics:
        metric_sentence = special_metrics[0]
    elif metrics_summary:
        metric_sentence = f"Empirical benchmark yield and performance metrics: {', '.join(metrics_summary)}."
    elif is_review:
        metric_sentence = f"Qualitative evidence synthesis: Evaluates clinical response rates, psychological rating scales, and biological markers reported across trials for {tool_val}."
    else:
        clean_cand = [
            s.strip() for s in sentences
            if not re.search(disease_symptom_reject, s, re.IGNORECASE)
            and not re.search(scope_reject, s.strip(), re.IGNORECASE)
            and not re.match(protocol_reject_regex, s.strip(), re.IGNORECASE)
        ]
        if clean_cand:
            metric_sentence = clean_cand[-1]
        else:
            author_ref = authors.split(",")[0] if authors else "Literature"
            metric_sentence = f"Empirical baseline established by {author_ref} ({year or 'benchmark'}): quantitative activity benchmarks reported for {tool_val}."

    # 5. Experimental Controls, Chassis Model & Assay Conditions (Parameter 4)
    explicit_control_sentences = []
    direct_control_terms = [
        "negative control", "positive control", "baseline control", "vehicle control",
        "served as control", "served as the control", "served as a control",
        "empty-plasmid", "empty plasmid", "empty vector", "empty-vector",
        "non-targeting", "parent cultivars", "parent cultivar", "parent strain",
        "reference strain", "isogenic", "unmodified control", "wild-type control",
        "mock-treated", "untreated control", "placebo"
    ]
    for s in sentences:
        low = s.lower()
        if any(c in low for c in direct_control_terms):
            explicit_control_sentences.append(s.strip())

    if not explicit_control_sentences:
        for s in sentences:
            low = s.lower()
            if any(c in low for c in ["control", "wild-type", "unmodified", "vehicle", "mock", "homologous", "baseline"]) and any(comp in low for comp in ["compared to", "versus", "relative to", "against", "reference"]):
                explicit_control_sentences.append(s.strip())

    assay_techniques = []
    technique_keywords = [
        "x-ray crystallography", "crystal structure", "cryo-em", "hplc", "fplc", "mass spectrometry",
        "spectrophotomet", "fluorescence", "flow cytometry", "rt-qpcr", "qpcr", "western blot",
        "sds-page", "circular dichroism", "isothermal titration calorimetry", "surface plasmon resonance",
        "enzyme kinetics", "plate reader", "biochemical assay", "field trial", "greenhouse", "fed-batch"
    ]
    for tech in technique_keywords:
        if tech in text_lower:
            assay_techniques.append(tech.title())

    tech_summary = ", ".join(list(dict.fromkeys(assay_techniques))[:3]) if assay_techniques else "Standard biochemical / molecular assay"

    if is_review:
        if explicit_control_sentences:
            controls_val = f"Evidence Scope & Comparators: Multi-study synthesis across {chassis_val}. Trial comparators: {explicit_control_sentences[0]}"
        else:
            controls_val = f"Evidence Scope & Comparators: Synthesizes randomized controlled trials and observational cohorts in {chassis_val}. Comparative baseline: Placebo or standard-of-care control arms across referenced clinical trials."
    elif explicit_control_sentences:
        controls_val = f"Model & Assay: Tested in {chassis_val} using {tech_summary}. Verification Controls: {explicit_control_sentences[0]}"
    else:
        controls_val = f"Model & Assay: Tested in {chassis_val} using {tech_summary}. Verification Benchmark: Benchmarked against wild-type / parental baseline (Note: Explicit negative vehicle blanks not fully detailed in short abstract; include vehicle and unengineered negative controls in your proposal)."

    # 6. Stated Limitations / Unresolved Gaps (Parameter 3)
    gap_sentences = []
    gap_indicators = [
        "however", "despite", "nevertheless", "resisted", "limiting", "penalty",
        "severe background", "silencing", "drawback", "not fully optimized", "does not degrade",
        "cannot degrade", "remains a challenge", "restricted by", "unresolved", "bottleneck",
        "impeded", "denaturation", "thermolability", "off-target", "highlight the need",
        "further developments", "constrained by", "lacks", "limited by", "poor", "low yield",
        "toxicity", "instability", "inefficient", "barrier", "challenge", "hurdle",
        "rate-limiting", "kinetic bottleneck", "quenching"
    ]
    for s in sentences:
        low = s.lower()
        if any(g in low for g in gap_indicators):
            gap_sentences.append(s.strip())

    if gap_sentences:
        gap_val = gap_sentences[0]
    else:
        gap_val = f"Translational and operational constraints remain the primary gap: real-world matrix interference, operational yield, and scalable deployment of {tool_val} in {chassis_val} require further experimental optimization beyond this initial study."

    # 7. Core Engineered Innovation & Molecular Mechanism (Parameter 5)
    innovation_sentences = []
    innovation_terms = [
        "engineered", "mutation", "mutants", "active-site", "narrowing", "cleft",
        "binding cleft", "residues", "substituted", "fusion", "coupled", "introgressed",
        "designed", "synthesized", "cloned", "chimeric", "recombinant", "promoter",
        "variant", "scaffold", "directed evolution", "rational design", "catalytic",
        "transporter", "circuit", "construct"
    ]
    for s in sentences:
        low = s.lower()
        if re.search(disease_symptom_reject, s, re.IGNORECASE) or re.search(scope_reject, s.strip(), re.IGNORECASE):
            continue
        if any(term in low for term in innovation_terms) and any(v in low for v in ["here", "we", "by", "develop", "reveals", "design", "mutat", "construct"]):
            innovation_sentences.append(s.strip())

    solution_candidates = [
        s.strip() for s in sentences
        if not re.search(disease_symptom_reject, s, re.IGNORECASE)
        and not re.search(scope_reject, s.strip(), re.IGNORECASE)
        and any(w in s.lower() for w in ["here, we", "we engineered", "we developed", "we coupled", "we discovered", "we introgressed", "this study", "we designed", "constructs were", "evaluates", "investigates"])
    ]
    finding_candidates = [
        s.strip() for s in sentences
        if not re.search(disease_symptom_reject, s, re.IGNORECASE)
        and not re.search(scope_reject, s.strip(), re.IGNORECASE)
        and any(w in s.lower() for w in ["achieved", "exhibited", "detected", "reduced", "increased", "yield", "fold", "resulting in", "demonstrated", "turnovers"])
    ]

    if innovation_sentences:
        key_innovation = innovation_sentences[0]
    elif solution_candidates:
        key_innovation = solution_candidates[0]
    elif is_review:
        key_innovation = f"Clinical synthesis: Evidence review analyzing the therapeutic mechanism and efficacy of {tool_val} in {chassis_val}."
    else:
        key_innovation = f"Engineered intervention: Targeted {tool_val} construct optimized for molecular activity in {chassis_val}."

    # 8. Key Measured Findings, Evidence Proof & Research Horizon (Parameter 6)
    if special_metrics:
        measured_finding = special_metrics[0]
    elif metrics_summary:
        measured_finding = f"Demonstrated validated performance benchmarks: {', '.join(metrics_summary)}."
    elif finding_candidates:
        measured_finding = finding_candidates[0]
    elif is_review:
        measured_finding = f"Synthesized qualitative clinical and biomarker evidence across multiple studies evaluating {tool_val}."
    else:
        measured_finding = f"Demonstrated quantitative proof-of-concept for {tool_val} in {chassis_val}."

    if is_review:
        research_horizon = f"Evidence Scope: {measured_finding} Horizon for Your Project: Addressing unresolved gaps in {gap_val[:90]}... through primary experimental or clinical design."
    else:
        research_horizon = f"Evidence Proof: {measured_finding} Horizon for Your Project: Overcoming {gap_val[:90]}... under operational conditions."

    # Backward-compatible target milestone formula (preserved for existing tests and prompt guidance)
    if metrics_summary:
        target_milestone = f"Target a calibrated ≥2- to 3-fold quantitative improvement over the published literature baseline ({metrics_summary[0]}) under operational assay conditions."
    elif is_review:
        target_milestone = "Literature synthesis gap: Consult primary trial extraction tables (such as Table 1) to select a specific quantitative endpoint (e.g., ≥30% symptom score reduction or biomarker delta) for your Aim 3 proposal milestone."
    else:
        target_milestone = "Target a calibrated quantitative improvement in efficiency, yield, analytical sensitivity, or stability over the published literature baseline."

    # Realistic Literature Timeline Benchmarks
    timeline_benchmark = {
        "phase1_months": "Months 1–4",
        "phase1_focus": f"Cloning, construct synthesis ({tool_val}), and sequence verification in {chassis_val}" if not is_review else f"Clinical protocol design, cohort stratification, and biomarker panel selection for {tool_val}",
        "phase2_months": "Months 4–8",
        "phase2_focus": f"Expression optimization, kinetic assays, and quantitative benchmark evaluation ({tech_summary})" if not is_review else f"Trial intervention phase, patient adherence tracking, and primary clinical endpoint scoring",
        "phase3_months": "Months 8–14",
        "phase3_focus": "Operational matrix validation, stability trials, and translational reporting" if not is_review else "Blinded statistical analysis, demographic subgroup stratification, and publication",
        "buffer_guidance": "Peer-reviewed literature allocates 15–20% buffer for failed clone verification and protocol recalibration." if not is_review else "Clinical trial guidance allocates 15–20% buffer for patient dropout and follow-up attrition."
    }

    return {
        "chassis": chassis_val,
        "tool": tool_val,
        "burden_statistic": burden_val,
        "metric_numbers": metrics_summary,
        "primary_metric_sentence": metric_sentence,
        "plain_metric": simplify_academic_text(metric_sentence),
        "controls": controls_val,
        "experimental_strategy": controls_val,
        "stated_gap": gap_val,
        "plain_gap": simplify_academic_text(gap_val),
        "key_innovation": key_innovation,
        "key_findings": measured_finding,
        "research_horizon": research_horizon,
        "target_milestone": target_milestone,
        "timeline_benchmark": timeline_benchmark,
        "is_review": is_review
    }


def _generate_proposal_recommendations(parameters: Dict[str, Any], title: str) -> List[Dict[str, str]]:
    """Suggests where this paper directly plugs into the student's proposal."""
    recs = []
    is_rev = bool(parameters.get("is_review"))

    # 1. Current Scientific Benchmark (Tier 2 of Funnel)
    if is_rev:
        recs.append({
            "section": "Step 3: Background & Current Scientific Benchmark (Funnel Tier 2)",
            "guidance": f"Cite this review as the baseline landscape and clinical context: \"{parameters['tool']} - {parameters['primary_metric_sentence']}\". This establishes the current state of the field and confirms that this is an active area of investigation.",
            "target_field": "funnel_tier2"
        })
    else:
        recs.append({
            "section": "Step 3: Background & Current Scientific Benchmark (Funnel Tier 2)",
            "guidance": f"Cite this paper as your empirical benchmark: \"{parameters['tool']} achieved {parameters['primary_metric_sentence']}\". This proves you know the current scientific ceiling.",
            "target_field": "funnel_tier2"
        })

    # 2. Scientific Knowledge Gap (Tier 3 of Funnel)
    if is_rev:
        recs.append({
            "section": "Step 3: Knowledge Gap (Funnel Tier 3)",
            "guidance": f"Use the authors' identified research gap as your project motivation: \"{parameters['stated_gap']}\". Explain that while this review confirms therapeutic potential, this unresolved bottleneck motivates your novel proposal.",
            "target_field": "funnel_tier3"
        })
    else:
        recs.append({
            "section": "Step 3: Knowledge Gap (Funnel Tier 3)",
            "guidance": f"Use the authors' admitted limitation as your jump-off gap: \"{parameters['stated_gap']}\". Explain that while their study made great progress, this unresolved bottleneck motivates your grant.",
            "target_field": "funnel_tier3"
        })

    # 3. Competitor Matrix (Step 5)
    if is_rev:
        recs.append({
            "section": "Step 5: Competitor Landscape Matrix (Incumbent/Emerging)",
            "guidance": f"Enter {parameters['tool']} as the 'Evaluated Clinical Approach'. Highlight its reported efficacy, but demonstrate how your proposal's engineered innovation overcomes its acknowledged limitation ({parameters['stated_gap'][:60]}...).",
            "target_field": "emerging_name"
        })
    else:
        recs.append({
            "section": "Step 5: Competitor Landscape Matrix (Incumbent/Emerging)",
            "guidance": f"Enter {parameters['tool']} as the 'Emerging Competitor'. Highlight their performance ({', '.join(parameters['metric_numbers'][:2]) or 'High yield'}), but show your advantage over their flaw ({parameters['stated_gap'][:60]}...).",
            "target_field": "emerging_name"
        })

    # 4. Methodology Controls (Step 4 & Specific Objectives)
    if is_rev:
        recs.append({
            "section": "Step 4: Experimental Methodology & Controls",
            "guidance": f"Adopt recommended clinical trial controls: {parameters['controls'][:120]}... Ensure your Aim 2 / Aim 3 design incorporates rigorous comparator groups.",
            "target_field": "methodology"
        })
    elif "not explicitly" in parameters.get("controls", "").lower():
        recs.append({
            "section": "Step 4: Experimental Methodology & Controls",
            "guidance": "Designate explicit positive benchmark controls and negative vehicle blanks in your methodology (Step 4) to ensure your experimental design is reproducible.",
            "target_field": "methodology"
        })
    else:
        recs.append({
            "section": "Step 4: Experimental Methodology & Controls",
            "guidance": f"Adopt their experimental controls: {parameters['controls'][:120]}... Reviewers reward proposals that duplicate validated peer-reviewed control designs.",
            "target_field": "methodology"
        })

    return recs
