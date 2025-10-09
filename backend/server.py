@@
 @api_router.post("/agent-builder/ask/gateway")
 async def builder_ask_gateway(body: AgentAskGatewayRequest):
@@
     return result
+
+# --- Flask-compat alias routes (Blueprint-style under /builder) ---
+@api_router.post("/builder/create_agent")
+async def builder_create_agent_compat(body: BuilderAgentCreate):
+    # Reuse core create and adapt response to Flask shape
+    created = await builder_create_agent(body)  # returns BuilderAgentOut
+    return {"status": "success", "agent": created}
+
+@api_router.get("/builder/list_agents")
+async def builder_list_agents_compat():
+    items = await builder_list_agents()
+    # Return plain list as Flask code did
+    return items
+
+@api_router.post("/builder/ask")
+async def builder_ask_compat(body: AgentAskRequest):
+    result = await builder_ask_agent(body)
+    return result
+
+@api_router.get("/builder/history")
+async def builder_history_compat(agent_id: str):
+    return await builder_agent_history(agent_id)
*** End Patch