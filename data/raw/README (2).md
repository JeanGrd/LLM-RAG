
<p align="center">
<img src="documentation/readmeimg/Moko.png" alt = "Moko">
</p>

## Summary

1) [Presentation](#Presentation)
2) [Installation](#Installation)
3) [How to create your own Jira reports](#How-to-create-your-own-Jira-reports)
4) [How to create your own Word templates](#How-to-create-your-own-Word-templates)
5) [Regulation](#Regulation)

# Presentation

Moko is an application for generating Word or Excel documents containing data extracted from Jira.
It also allows you to make personalized Jira reports in order to better follow your project, whether for clients or even documents summarizing the progress of the project.

How it works? Moko uses a python class called "JiraReport" which transforms an XML document into pandas DataFrame. This XML file contains the structure of a Jira report.
This class will then make it possible to insert this data directly into a Word or Excel document according to your choice.

In order to push the automation as much as possible, you can create Word templates in which you will define the place where your tables containing the extracted Jira data should be placed.
If no template exists, the program will create a classic Word document anyway.

Wishing you a pleasant use of Moko, you can contact me if you need more information.

### Example of reports:

For example, I have made this reports:
```xml
<File name="Jira reports" reference="" project="">
    <Table name="First table" style="Classic" keyword="FirstTest">
        <JQL>project = "LS" ORDER BY created DESC</JQL>
        <Column name="Title" type="">summary</Column>
        <Column name="Reference" type="">summary</Column>
        <Column name="issue" type="">description</Column>
        <Column name="Classification" type="">summary</Column>
    </Table>

    <Table name="Second table" style="Classic" keyword="SecondTest">
        <JQL>project = "LS" AND "nb" is 3 ORDER BY created DESC</JQL>
        <Column name="Title" type="">summary</Column>
        <Column name="Reference" type="">summary</Column>
        <Column name="issue" type="">description</Column>
        <Column name="Classification" type="">summary</Column>
    </Table>
</File>
```

Moko has developed these documents:

**1) Excel** (.xlsx)

<p align="center">
<img src="documentation/readmeimg/Excel.PNG" alt = "Excel">
</p>

**2) Word** (.docx)

<p align="center">
<img src="documentation/readmeimg/Word.png" alt = "Diagram" >
</p>

**3) Template Word** (.docx)

<p align="center">
<img src="documentation/readmeimg/WordTemplate.png" alt = "Diagram">
</p>

# Installation

**Warning:** Before use check if the version of my code is compatible with yours (python 3.8)

### 1) Installation of libraries

To be able to use the code entirely, you must have a set of libraries that are used for the proper functioning of the code:

If a library is missing then you can look at the level of the header of the code, you will find all the libraries used there.

```python
pip install jira
pip install tk-tools
pip install xlsxwriter
pip install python-docx
pip install os-sys
pip install elementpath
pip install threaded
pip install python-certifi-win32
pip install pandas
pip install requests 
```

### 2) Initialisation

You just have to enter the URL of your Jira server in the initialisation.py file: 

```python
jira_server = 'https://myjiraserver.com/'   # Jira server URL  
```

### 3) Configuration of Moko combobox

This XML file **(.../configuration/config.xml)** allows you to manage all the document templates that you will have created beforehand. 
Concretely, it is used to keep these templates to call them more quickly later.

#### Example of a configuration file:

```xml
<configuration>
    <type name="FirstType"> <!-- Block of documents -->
        <document name = "Test" template="SIMPLE-REPORTS.docx">test.xml</document> <!-- Document -->
    </type>

    <type name="SecondType">
        <document name = "Test 1 Second" template="">test1second.xml</document>
        <document name = "Test 2 Second" template="">test2second.xml</document>
    </type>

    <type name="ThirdType">
        <document name = "Test 1 Third" template="SIMPLE-REPORTS.docx">test1third.xml</document>
        <document name = "Test 2 Third" template="SIMPLE-REPORTS.docx">test2third.xml</document>
        <document name = "Test 3 Third" template="">test3third.xml</document>
    </type>
</configuration>
```

Once the program is launched, you will see that there are the three types of document you specified.
You can also see that there is a last field which is mandatory **"Generate Custom File"** which allows you to manually select an XML file in your directory and generate it.

<p align="center">
<img src="documentation/readmeimg/config.png" alt = "Moko">
</p>

> **Note:** the 'template' attribute is not necessary, it allows you to put the Jira data in your own template (see 'How to create a Word template' below).

# How to create your own Jira reports

To work properly, the program needs to be given an architecture. 
This architecture is given by the XML format, it is very easy to adjust your report as you wish in order to obtain the most adequate report.

This file is the most important because it defines the structure of our document. This allows the program to be much more flexible and to create documents of any type. 

##### Example: 

```xml
<File name="Template">
    <Table name = "MyMultipleFiltersArray" style = "MultipleFilters">
        <Filters>
            <JQL name="MyFirstElement">project = MyProject AND "Key" ~ "T*" ORDER BY "Document"</JQL>
            <JQL name="MySecondElement">project = MyProject AND "Name" ~ "I*"</JQL>
        </Filters>
        <Column name = "Id." type="">customfield_20000</Column>
        <Column name = "Title" type="">summary</Column>
        <Column name = "Reference" type="">customfield_30000</Column>
        <Column name = "Issue" type="">customfield_30000</Column>
        <Column name = "Version" type="">versions</Column>
    </Table>
    
    <Table name = "MyClassicalArray" style = "Classic">
        <JQL>project = MyJQLQuery</JQL>
        <Column name = "Id." type="">customfield_20000</Column>
        <Column name = "Title" type="">summary</Column>
        <Column name = "Reference" type="">customfield_30000</Column>
        <Column name = "Issue" type="">customfield_30000</Column>
        <Column name = "Version" type="">versions</Column>
    </Table>
</File> 
```

The first **File** tag is the first step in creating a template.
First you have to give it a name, for my part I called it **Template**. 
From this moment, you can already generate this template even if the document will be empty with only the name at the top of the page.

#### I distinguish two types of tables:

1. Classic table with a single JQL query (which I call **Classic**)
2. Table with the possibility to put several JQL queries (which I call **MultipleFilters**)

## Tag: Table

In my example, it is the second tag in the **File** tag.
This tag is called **Table** and contains its **name** and its **style**.

```xml
<Table name = "" style = ""></Table>
```
### Attribute: name

Defines the name of the table you want to create.

```xml
<Table name = "TableName" style = ""></Table>
```

### Attribute: style

Defines the shape of the table we want to create. 
As explained before, we have two different styles:

- **Classic table**

```xml
<Table name = "TableName" style = "Classic"></Table>
```

This result in:

<br>  
<center><img src="documentation/readmeimg/ClassicArray.PNG" alt = "Moko" width="625"></center>
<br>

- **Multiple JQL table**

```xml
<Table name = "TableName" style = "MultipleFilters"></Table>
```

This result in:

<br>  
<center><img src="documentation/readmeimg/MultipleFilters.PNG" alt = "Moko" width="625"></center>
<br>

## **Tag: JQL**

This tag allows you to fill in the JQL query on which you want to retrieve all the questions.
The attributes are different between the Classic table and the MultipleFilters table:

- **Classic table**

```xml
<JQL>project = MyJQLQuery</JQL>
```

- **Multiple JQL table**

```xml
<Filters>
    <JQL name = "JQLName1"></JQL>
    <JQL name = "JQLName2"></JQL>
    <JQL name = "JQLName3"></JQL>
</Filters>
```

The **name** attribute in the multiple JQL specifies the title of your JQL query (see above the result).

## **Tag: Column**

The last tag that we find in the table tag is the column tag.
It allows you to define all the columns of the table that you want to generate.
You can add as many column tags as you want.

```xml
<Column name = "" type=""></Column>
```

### Attribute: name

Defines the name of the column.

**Example :**

```xml
<Column name = "MyColumnName" type=""></Column>
```

### Attribute: type

Defines the type of data you want to export. For me, there are 3 types of data: 
Classic data, Linking data, and Multiple value data. 
**This is what the link attribute does.**

#### Value: Nothing

If you retrieve a classic data like summary then is not necessary to put value in type attribute.

```xml
<Column name = "MyColumnName" type="">summary</Column>
```

> Note: Even if you have nothing to fill in, you must still put the name of the attribute as above

#### Value: link

Defines if you use a linking data.  

Example:

```xml
<Column name = "MyColumnName" type="link">is superseded by</Column>
```

#### Value: multiple_values

Defines if the field has multiple values or not.
This option is used when a field in Jira can contain several values.
This option will retrieve all the values of the field and return them in the desired column.

Example:

```xml
<Column name = "versions" type="multiple_values">versions.name</Column>
```  

## List of fields in Jira

The field in Jira is a sometimes complicated element to retrieve, so some fields are particular to retrieve. 
Earlier we saw the management of **link** fields and fields with **multiple values**.

Multiple fields in Jira are easily identifiable, 
if in the table you have a cell with this kind of text inside after a classic import:

```
[<Jira Component:name='Projet1', id='00000'>, <Jira Component:name='Projet1', id='00000'>, ...]
```

You also have fields with several types in the same field, for example :

```
[<Jira MyField:name='Projet1', id='00000', category='Import'>]
```

If after your import you get this result, then you have to add which type you want to import. In our example we want the field **name** so we have to write :

```xml
<Column name = "Title" type="multiplevalues">MyField.name</Column>
```

## Non-exhaustive list of fields

To help you develop a template I propose a list of frequently used fields in Jira :

- summary 

It returns the name of the issue.

```xml
<Column name = "Title" type="">summary</Column>
```

- versions 

Version you have assigned to your issue, this field can have several values. 

```xml
<Column name = "Versions" type="">versions</Column>
```

- fixversion 

Corrected version of your issue, this field can have several values.

```xml
<Column name = "Fixversion" type="">fixVersions</Column>
```

- components

The components of your issue, this field can have several values.

```xml
<Column name = "Components" type="">components</Column>
```

- issuetype

Returns the type of the issue.

```xml
<Column name = "Issuetype" type="">issuetype.name</Column>
```

- status

Return the status of the issue.
  
```xml
<Column name = "Status" type="">status.name</Column>
```

- assignee

Returns the people who are assigned to the issue.

```xml
<Column name = "Assignee" type="">assignee</Column>
```

- creator

Returns the creator of the issue.

```xml
<Column name = "Creator" type="">creator</Column>
```

- reporter

Returns the reporter of the issue

```xml
<Column name = "Reporter" type="">reporter</Column>
```

- created

Returns the date the issue was created.

```xml
<Column name = "Created" type="">created</Column>
```

- labels

Returns the label field of the issue.

```xml
<Column name = "Labels" type="">labels</Column>
```

- description

Returns the description of the issue.

```xml
<Column name = "Description" type="">description</Column>
```

- project

Returns the current project of the issue. 

```xml
<Column name = "Project" type="">project</Column>
```

- resolution

Returns the resolution of the issue.

```xml
<Column name = "Resolution" type="">resolution</Column>
```

- resolutiondate

Returns the date the issue was resolved.

```xml
<Column name = "Resolution date" type="">resolutiondate</Column>
```

- updated

Returns the date the issue was updated.

```xml
<Column name = "Updated" type="">updated</Column>
```

- subtask

Returns the secondary tasks of the issue.

```xml
<Column name = "Subtask" type="">issuetype.subtask</Column>
```

- status_description

Returns the description of the status of the issue.

```xml
<Column name = "Status description" type="">status.description</Column>
```

- watchcount

Returns the number of people who opened the issue.

```xml
<Column name = "Watch count" type="">watches.watchCount</Column>
```

- customfield_... (depends on the value of the customfield, you can easily find the value of your customfield in the XML file when exporting an issue to Jira)

```xml
<Column name = "Watch count" type="">customfield_...(To be completed)</Column>
```

## Other fields

So this was a non-exhaustive list of fields that we can extract from Jira.

To know all your fields on your Jira, go here:

    https://myserverjira/rest/api/2/field 

**(To be adapted according to your URL)**

# How to create your own Word templates

For this chapter, I'll walk you through how to create your own Word templates with a step-by-step example.

### 1) Open a new document in Word

Above all, do not use a word processor other than Word because others can create errors.
You can put what you want in this document. There are no limit.

<br>  
<center><img src="documentation/readmeimg/Template1.PNG" alt = "Template" width="625"></center>
<br>

### 2) Create a new table 

If you want to recover an import, it is necessary to create the table that will receive the new data.

You must create the table with the correct number of columns, if the number of columns is incorrect, the import will not work.

The first line of your table will not be modified, it defines the name of your columns.

<br>  
<center><img src="documentation/readmeimg/Template2.PNG" alt = "Template" width="625"></center>
<br>

### 3) Define the data to be imported

You must add a second line.
In this line you add the 'keyword' (given in the xml template) to the first box.

After that, you can enjoy your template Word.

```xml
<Table name = "MyClassicalArray" style = "Classic" keyword="keyword_t">
    <JQL>project = MyJQLQuery</JQL>
    <Column name = "Column1" type="">customfield_20000</Column>
    <Column name = "Column2" type="">summary</Column>
    <Column name = "Column3" type="">customfield_30000</Column>
    <Column name = "Column4" type="">customfield_30000</Column>
</Table>
```

<br>  
<center><img src="documentation/readmeimg/Template3.PNG" alt = "Template" width="625"></center>
<br>

> **Note:** don't forget to specify the word document in the configuration_interface.xml file (see [Installation](#Installation))

# Regulation

This code is protected by the copyright which is conferred to him thanks to a solution of timestamp. 
Therefore, you are not entitled to claim ownership.
If you are going to publish this code, you must quote me.

Nevertheless, it remains free. Wishing you a good use of this program.

**Company**: Thales Alenia Space (www.thalesaleniaspace.com)
\
**Project:** Moko (version : 6.1.2)
\
**Author:** Jean Guiraud
