## Problem solving explanation

### Gathering all the rules

Reading the QR code led to a website containing information of "Arturic Industries", mocking an institutional page with rules for processing data for the quarterly output files, with information inside the following tabs:
- The "Directory" had all the valid values for the Departments, Processors, Bins and Categories variables;
- The "Processing Manual" had rules 1 to 6, expanding on the "Directory" information with the value above zero and timestamp validation rules;
- The "Compliance Annex" first required a password to access the supplementary rules. After inserting the password, a page with rules 7 to 11 was revealed. These rules detailed data refinement needed to be done to only account for valid sessions and entries, like values needing to be below 1000 or processor Nora.K's termination date.

### Finding the password

By analyzing the source code from the compliance tab I found the script portion of the `html` code making a comparison with the `38b19f2e76c9fa1e3ab74c80fb3e95b3cd761ce39b0e2359b6ac15e012220907` string and the hashed capitalized password. If both were equal, then the password was joined with the "arturic" word and hashed, and the result would be the redirect path to the last rules.
To find the answer, I ran a list of known passwords hashed against the target hash, and discovered the password to be "JANSKY". To verify if the answer made sense, I read the metadata of the "facility_exterior.png" file (that according to the website had a clue) with a GPS location pointing to a sign containing the word "JANSKY", revealing the final rules.

### Building the code

Since we had 3 types of files, I decided to write one function for each type to process the data. After the data was extracted, I first validated it against the session-related rules, including the "duplicate session" rule. If the data was valid, then each entry was validated against the entry rules, excluding invalid ones and adding the value to find out the required sum.

### Final sum
**1023118.20**

### Found anomalies
- Files with session not belonging to the correct folder (e.g. MDR file in the SA folder);
- Invalid session data (e.g. HR department, unknown processor, weekend/outside of Q4 2025 timestamps), totaling 63 occurrences;
- Invalid entry data (e.g. sigma category, out of range/non-numeric values), totaling 444 occurrences.