import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { signupSchema, loginSchema } from "@shared/schema";

export async function registerRoutes(app: Express): Promise<Server> {
  app.post("/api/auth/signup", (req, res) => {
    try {
      const data = signupSchema.parse(req.body);
      
      const existingUser = storage.getUserByEmail(data.email);
      if (existingUser) {
        return res.status(400).json({ error: "Email already in use" });
      }

      const user = storage.createUser(data);
      
      const { password, ...userWithoutPassword } = user;
      res.json({ user: userWithoutPassword });
    } catch (error: any) {
      res.status(400).json({ error: error.message || "Invalid input" });
    }
  });

  app.post("/api/auth/login", (req, res) => {
    try {
      const data = loginSchema.parse(req.body);
      
      const user = storage.getUserByEmail(data.email);
      if (!user || user.password !== data.password) {
        return res.status(401).json({ error: "Invalid email or password" });
      }

      const { password, ...userWithoutPassword } = user;
      res.json({ user: userWithoutPassword });
    } catch (error: any) {
      res.status(400).json({ error: error.message || "Invalid input" });
    }
  });

  const httpServer = createServer(app);

  return httpServer;
}
