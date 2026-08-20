### Delete the database

First, make sure you're **not connected to the** **`litellm`** **database**:

```bash
sudo -u postgres psql -c "DROP DATABASE litellm;"
```

If PostgreSQL says the database is being accessed by other users, terminate the connections:

```bash
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'litellm' AND pid <> pg_backend_pid();"
```

Then:

```bash
sudo -u postgres psql -c "DROP DATABASE litellm;"
```

### Delete the owner/user

After deleting the database:

```bash
sudo -u postgres psql -c "DROP USER litellm;"
```

### Verify

```bash
sudo -u postgres psql -c "\l"
```

and:

```bash
sudo -u postgres psql -c "\du"
```

You should no longer see the `litellm` database or `litellm` role.

**So, the complete cleanup is:**

```bash
sudo -u postgres psql -c "DROP DATABASE litellm;"
sudo -u postgres psql -c "DROP USER litellm;"
```
