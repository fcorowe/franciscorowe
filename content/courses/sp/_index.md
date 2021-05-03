---
date: "2020-02-01"
linkTitle: Spatial Analysis
summary: This is an introductory course to spatial analysis and modelling using R.
title: "\U0001F4CA Spatial Analysis"
type: book
---

{{< figure src="featured.jpg" >}}

{{< toc hide_on="xl" >}}

## Module Aims

This module aims to:

- Build upon the more general research training delivered via companion modules on {{<hl>}}Data Collection and Data Analysis{{</hl>}}, which have an aspatial focus;
- Highlight the spatial dimension of key social issues;
- Explain the specific challenges faced when attempting to analyse spatial data;
- Introduce a range of analytical techniques and approaches suitable for spatial data analysis; and,
- Enhance practical skills in using software packages to implement spatial analytical tools.

## Module Learning Outcomes

You will learn how to:

- Identify key sources of spatial data and resources for {{<hl>}}spatial analysis and modelling{{</hl>}}
- Explain the advantahes of taking {{<hl>}}the hierarchical structure of spatial data{{</hl>}} into account for data analysis
- Apply a range of computer-based techniques for spatial data analysis, including {{<hl>}}mapping, correlation, kernel density estimation, regression, multilevel modelling, geographically weighted regression, spatial interaction modelling and spatial econometrics{{</hl>}}
- Apply appropriate analytical approaches to tackle key methodological challenges often found in spatial analysis, such as {{<hl>}}spatial autocorrelation, spatial heterogeneity, the ecological fallacy{{</hl>}} 
- Select appropriate analytical tools for the {{<hl>}}analysis of specific types of spatial data{{</hl>}} to address emerging societal issues

Achievement of these outcomes will be assessed via coursework.

## Module Programme

* [Week 1. Introduction & Spatial Data](https://vital.liv.ac.uk): [R Notebooks + Basic Functions + Data Types](https://gdsl-ul.github.io/san/)

* [Week 2. Point Data Analysis](https://gdsl-ul.github.io/san/points.html): [Kernel Density Estimation & Spatial Interpolation](https://gdsl-ul.github.io/san/points.html)

* [Week 3. Flow Data Analysis](https://gdsl-ul.github.io/san/flows.html): [Spatial Flows Estimation](https://gdsl-ul.github.io/san/flows.html)

* [Week 4. Spatial Econometrics](https://gdsl-ul.github.io/san/spatial-econometrics.html): [Spatial Regression](https://gdsl-ul.github.io/san/spatial-econometrics.html)

* Week 5: Assignment 1 Clinic

* [Week 6. Multilevel Modelling 1](https://gdsl-ul.github.io/san/multilevel-modelling-part-1.html): [Multilevel Modelling – Random Intercept Multilevel Model](https://gdsl-ul.github.io/san/multilevel-modelling-part-1.html)
    
* [Week 7. Multilevel Modelling 2](https://gdsl-ul.github.io/san/multilevel-models-pt-ii.html): [Multilevel Modelling – Random Slope](https://gdsl-ul.github.io/san/multilevel-modelling-part-2.html)
        
* Week 8: Assignment 2 Clinic

* **Week 9: No Teaching (field class week)**

* [Week 10: Geographically Weighted Regression](https://gdsl-ul.github.io/san/geographically-weighted-regression.html): [Spatial Nonstationarity](https://gdsl-ul.github.io/san/geographically-weighted-regression.html)


* [Week 11: Spatio-Temporal Data Analysis](https://gdsl-ul.github.io/san/spatio-temporal-analysis.html): [Spatio-temporal modelling](https://gdsl-ul.github.io/san/spatio-temporal-analysis.html)

* Week 12: Assignment 3 Clinic


## Module Delivery

The module is structured around weekly lecture and practical sessions, involving 9 teaching sessions and 3 clinic sessions - one before each module assignment. The teaching sessions provide both theoretical exposition and hands-on practical experience of the issues and challenges on handling spatial data and a wide range of analytical tools for their analysis and modelling.

Access to materials, including computational notebooks, is centralised through the use of a course website available in the following url: **franciscorowe.com/courses/sp/**

Specific readings, videos, and/or podcasts, as well as academic references will be provided for each lecture and practical session, and can be accessed through the course website.

## Assessment

The final module mark is composed of the {{<hl>}}three assignments{{</hl>}}. Together they are designed to cover the materials introduced in the entirety of content covered during the semester.

* Assignment 1 (33%)
* Assignment 2 (33%)
* Assignment 3 (34%)

Assignments will be prepared in the R Notebook format and then converted into
a self-contained HTML file that will then be submitted on Turnitin.

Submission is electronic only via Turnitin on VITAL.

Maximum word count: 1,500 words, excluding figures and references. As per School Assessment Guidelines, *over-length submission will be capped at 40%*. The assignment deadline is specified below. Assignments submitted after this deadline will be penalised 5% per working day late. Assignments submitted more than five working days late will be awarded a mark of zero. *Mitigating Circumstances* for late submission must be submitted for consideration via the Student Support Office (Ground Floor, Roxby Building; email: soessouth@liverpool.ac.uk).

{{<hl>}}Marking criteria{{</hl>}}: Standard Environmental Sciences School marking criteria apply, with a stronger emphasis on evidencing the use of regression models, critical analysis of results and presentation standards.

### Assignment 1

Assigment 1 assesses teaching content from Weeks 1 to 4. 

**Deadline**: 14:00pm, March 3rd, 2020.

Using a new batch of house prices from the Land Registry (see data provided), carry out the
following analysis in an analogous way to how they were performed in class:

* KDE of house transactions.

* Create a surface map of the house prices in the dataset. To do that, use spatial
interpolation and, in particular, an inverse distance weight approach.

* Fit several regression models to explain the (log of) house prices as a function of whether
they are newly built houses and the IMD score of the area where they are located. Include
at least:
1. Baseline non-spatial regression.
2. Spatial FE estimation based on two-digit postcodes.
3. Baseline regression with an additional spatial lag of the IMD Score (Note you will have to
select a spatial weights matrix and justify it.)

* Discuss the model estimation results, particularly:

    - Think about the advantages and limitations of modelling house prices with a spatial FE model,
especially from the perspective of the structure of housing price data.
    - If the higher-level units were LSOAs (rather than the two-digits postcode geographical
units) and LSOA dummy variables were used in the spatial fixed effect model, could you still
obtain the regression coefficients of the IMD score variable? Hint: IMD scores are also
measured at the LSOA level.

*Data*

Data to complete the assignment will be available on VITAL. The shapefile contains house
price information for Liverpool in 2014 (same data used in practice).

### Assignment 2 

Assigment 2 assesses teaching content from Weeks 6 and 7.

**Deadline**: 14:00pm, March 31st, 2020.

Following the examples in class:

* Fit various regression models to your dependent variable of choice as a function of at least three independent variables at your level 1 scale and at least one at you level 2 scale or higher orders. Include at least:
1. A OLS regression model;
2. A null multilevel (baseline) regression model;
3. A random intercept model;
4. A random slope model or a random intercept + slope model;

* Provide a short justification of the independent variables included in your models;

* Justify the inclusion of the chosen variable in your level-2 or higher scales;

* Create caterpillar plots and/or maps to visualise the extent of variation in the estimated random effects in your models;

* Analyse and discuss:
1. the extent of variation in the dependent variables at two or more geographical scales (variation at which geographical scale explains most of variance in your dependent variable);
2. the random intercept estimate(s) from your model(s) (what can they tell you about the difference between groups / areas? are they statistically significantly different?);
3. the random slope estimate(s) from your model(s) (to what extent does the relationship between your dependent and independent variables vary across groups / areas? are they statistically significantly different?).

Ensure you appropriately describe the structure of the data and identify the various geographical scales of analysis (i.e. level-1, level-2 or higher-level units)

*Data*

Data to complete the assignment are available on VITAL. Alternatively you can source your own data.

### Assignment 3

Assigment 3 assesses teaching content from Weeks 10 and 11. 

**Deadline**: 14:00pm, May 8th, 2020.

Following the examples in class:
* Fit various regression models to your dependent variable of choice as a function of at least three independent variables. Include at least:

1. A OLS regression model;
2. A Geographically Weighted Regression (GWR) model;
3. A spatio-temporal (SP) regression model;
4. A visual SP representation of your variables;

* Analyse and discuss:
1. How the OLS, GWR and SP results differ (How do regression coefficients vary across space? Is this variation statistically significant?)
2. How do coefficients change over time? Why? 
2. Are GWR and/or SP models needed? Why? 
3. What is the appropriate bandwidth for your GWR? Why?

*Data*

Data to complete the assignment are available on VITAL. Alternatively you can source your own data.


## Software

The module will use R as the primary software package. 

### On Campus PCs

If not pre-installed ie. no R and RStudio icons on your desktop:

* Right-click on the Windows icon at the bottom left of the screen
* Scroll down the list of available programs to find the *Install University Applications* option and click on this option
* Respond ‘Yes’ ‘Allow to make changes to this PC’ prompt
* Select the Statistics category
* Select the RStudio

This will automatically install both R and RStudio

### Personal computers

To install R, go to http://www.r-project.org/ > CRAN > select *mirror* site > and download and install the version relevant to your computer.

To install RStudio go to http://www.rstudio.com and download the relevant *Installer for supported platforms*.

## Feedback

Written feedback on the summative assignment will be provided within three working weeks of the
submission deadline.

Verbal feedback on understandings of all module material will be provided during lectures and labs sessions if requested. Students will also be offered the opportunity for one-to-one feedback, should they require it.

## Meet your instructor

{{< mention "admin" >}}

{{< cta cta_text="Begin the course" cta_link="https://gdsl-ul.github.io/san/" >}}
