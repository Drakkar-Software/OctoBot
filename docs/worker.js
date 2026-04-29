export default {
  async fetch() {
    return new Response("Not found", { status: 404 });
  },
};
