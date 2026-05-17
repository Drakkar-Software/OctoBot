import { test } from "node:test";
import assert from "node:assert/strict";
import {
  stripHttpImport,
  dateFieldsToString,
  enumBlockToUnion,
  narrowDiscriminatorField,
  collectVariantNarrowings,
} from "../scripts/postprocess-protocol-typescript.lib.mjs";

test("stripHttpImport removes the broken HttpFile import line", () => {
  const src = "import { HttpFile } from '../http/http';\nexport type X = string;\n";
  assert.equal(stripHttpImport(src), "export type X = string;\n");
});

test("stripHttpImport leaves source untouched when no HttpFile import", () => {
  const src = "export type X = string;\n";
  assert.equal(stripHttpImport(src), src);
});

test("dateFieldsToString rewrites Date typings to string", () => {
  const src = "    'created_at'?: Date;\n    'updated_at': Date;\n";
  assert.equal(
    dateFieldsToString(src),
    "    'created_at'?: string;\n    'updated_at': string;\n",
  );
});

test("dateFieldsToString leaves non-Date typings alone", () => {
  const src = "    'count'?: number;\n";
  assert.equal(dateFieldsToString(src), src);
});

test("enumBlockToUnion converts string enums to literal unions", () => {
  const src = "export enum Color {\n  Red = 'red',\n  Blue = 'blue'\n}";
  assert.equal(enumBlockToUnion(src), "export type Color = 'red' | 'blue'");
});

test("enumBlockToUnion leaves non-string enums untouched", () => {
  const src = "export enum Code {\n  Ok = 200,\n  NotFound = 404\n}";
  assert.equal(enumBlockToUnion(src), src);
});

test("narrowDiscriminatorField replaces shared enum reference with literal", () => {
  const src = "export class MM {\n    'configuration_type'?: ActionConfigurationType;\n    'pair_settings': string[];\n}\n";
  const out = narrowDiscriminatorField(src, "configuration_type", "market_making");
  assert.match(out, /'configuration_type'\?:\s*'market_making';/);
});

test("narrowDiscriminatorField handles required field (no `?`)", () => {
  const src = "    'action_type': UserActionType;\n";
  const out = narrowDiscriminatorField(src, "action_type", "automation_create");
  assert.equal(out, "    'action_type': 'automation_create';\n");
});

test("narrowDiscriminatorField leaves attributeTypeMap string entries alone", () => {
  const src = `    [\n        {\n            "name": "configuration_type",\n            "baseName": "configuration_type",\n            "type": "ActionConfigurationType",\n            "format": ""\n        }\n    ];\n`;
  const out = narrowDiscriminatorField(src, "configuration_type", "market_making");
  assert.equal(out, src);
});

test("narrowDiscriminatorField does not match other fields", () => {
  const src = "    'name'?: string;\n    'configuration_type'?: ActionConfigurationType;\n";
  const out = narrowDiscriminatorField(src, "configuration_type", "market_making");
  assert.match(out, /'name'\?:\s*string;/);
  assert.match(out, /'configuration_type'\?:\s*'market_making';/);
});

test("collectVariantNarrowings reads $ref+description properties", () => {
  const openapi = {
    components: {
      schemas: {
        ActionConfigurationType: { type: "string", enum: ["market_making", "dca"] },
        MarketMakingConfiguration: {
          properties: {
            configuration_type: {
              $ref: "#/components/schemas/ActionConfigurationType",
              description: "market_making",
            },
            pair_settings: { type: "array" },
          },
        },
        DCAConfiguration: {
          properties: {
            configuration_type: {
              $ref: "#/components/schemas/ActionConfigurationType",
              description: "dca",
            },
          },
        },
      },
    },
  };
  const result = collectVariantNarrowings(openapi);
  assert.deepEqual(result.get("MarketMakingConfiguration"), [
    { field: "configuration_type", literal: "market_making" },
  ]);
  assert.deepEqual(result.get("DCAConfiguration"), [
    { field: "configuration_type", literal: "dca" },
  ]);
});

test("collectVariantNarrowings ignores properties without description", () => {
  const openapi = {
    components: {
      schemas: {
        Foo: {
          properties: {
            kind: { $ref: "#/components/schemas/Kind" },
          },
        },
      },
    },
  };
  assert.equal(collectVariantNarrowings(openapi).size, 0);
});

test("collectVariantNarrowings ignores properties without $ref", () => {
  const openapi = {
    components: {
      schemas: {
        Foo: {
          properties: {
            kind: { type: "string", description: "some kind" },
          },
        },
      },
    },
  };
  assert.equal(collectVariantNarrowings(openapi).size, 0);
});

test("collectVariantNarrowings returns empty map on empty spec", () => {
  assert.equal(collectVariantNarrowings({}).size, 0);
});
