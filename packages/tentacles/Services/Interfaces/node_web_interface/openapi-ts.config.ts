import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./openapi.json",
  output: "./src/client",

  plugins: [
    {
      name: "@hey-api/client-axios",
      runtimeConfigPath: "./src/lib/hey-api-client-config",
    },
    {
      name: "@hey-api/sdk",
      operations: {
        strategy: "byTags",
        containerName: "{{name}}Service",
        nesting: "operationId",
        methods: "static",
      },
    },
    {
      name: "@hey-api/schemas",
      type: "json",
    },
  ],
})
