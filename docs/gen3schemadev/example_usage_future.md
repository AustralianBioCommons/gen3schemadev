# Example Usage
- What a future state may look like


## Introduction to data modelling

## Gen3 data modelling

## Usage

### Installation
```
pip install gen3schemadev
```


### Setup
```
gen3schemadev init
```

### Generate schemas
```
gen3schemadev generate -i input.yaml -o output/
```

### Bundle Schemas
```
gen3schemadev bundle -i yamls/ -o output/bundled_schema.json
```


### Validate schema
```
gen3schemadev validate -i bundled_schema.json
```

### Visualize schema
```
gen3schemadev visualize -i bundled_schema.json
```

