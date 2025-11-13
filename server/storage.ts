import { randomUUID } from "crypto";
import type { User, SignupInput } from "@shared/schema";

export interface IStorage {
  getUserByEmail(email: string): User | undefined;
  getUserById(id: string): User | undefined;
  createUser(data: SignupInput): User;
  getAllUsers(): User[];
}

export class MemStorage implements IStorage {
  private users: Map<string, User> = new Map();

  constructor() {
    // Initialize storage
  }

  getUserByEmail(email: string): User | undefined {
    return Array.from(this.users.values()).find(user => user.email === email);
  }

  getUserById(id: string): User | undefined {
    return this.users.get(id);
  }

  createUser(data: SignupInput): User {
    const user: User = {
      id: randomUUID(),
      ...data,
    };
    this.users.set(user.id, user);
    return user;
  }

  getAllUsers(): User[] {
    return Array.from(this.users.values());
  }
}

export const storage = new MemStorage();
