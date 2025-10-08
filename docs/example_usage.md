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
gen3schemadev generate -i tests/input_example.yml -o output/
```

### Bundle Schemas
```
 gen3schemadev bundle -i output -f output/test_schema_bundle.json
```


### Validate schema
```
gen3schemadev validate -b output/test_schema_bundle.json
```

### Visualize schema
```
gen3schemadev visualize -i bundled_schema.json
```

