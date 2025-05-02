#!/usr/bin/env node

import { Command } from 'commander';
import { config } from 'dotenv';
import { VERSION, startServer, ServerOptions } from './server';
import { createClient, LinodeClient } from './client';
import { TOOL_CATEGORIES, ToolCategory } from './tools';

// Load environment variables from .env file
config();

// Export key components for programmatic use
export { startServer, ServerOptions };
export { createClient, LinodeClient };
export { VERSION };

// Define CLI program
const program = new Command();

program
  .name('linode-mcp-server')
  .description('MCP server for Linode API integration with Claude Desktop')
  .version(VERSION);

program
  .option('-t, --token <token>', 'Linode API token')
  .option(
    '-c, --categories <categories>', 
    `Tool categories to enable (comma-separated). Available: ${TOOL_CATEGORIES.join(', ')}`, 
    (val) => val.split(',').map(c => c.trim())
  )
  .option('--list-categories', 'List all available tool categories')
  .option('--transport <type>', 'Transport type: stdio (default), sse, http', 'stdio')
  .option('--port <port>', 'Server port (default: 8080 for HTTP, 3000 for SSE)', 'default')
  .option('--endpoint <endpoint>', 'Server endpoint path (default: /mcp for HTTP, /sse for SSE)', 'default')
  .option('--host <host>', 'SSE server host (default: 127.0.0.1)', '127.0.0.1')
  .action(async (options) => {
    // If --list-categories was specified, show available categories and exit
    if (options.listCategories) {
      console.log('Available tool categories:');
      TOOL_CATEGORIES.forEach(cat => console.log(`- ${cat}`));
      process.exit(0);
    }

    // Check for token in command line args, then env var, then .env file
    const token = options.token || process.env.LINODE_API_TOKEN;

    // Ensure the token is provided
    if (!token) {
      console.error('Error: Linode API token is required');
      console.error('Please provide a token with --token option or set LINODE_API_TOKEN environment variable');
      process.exit(1);
    }

    // Validate categories if provided
    let enabledCategories: ToolCategory[] | undefined = undefined;
    
    if (options.categories && options.categories.length > 0) {
      // Check each category is valid
      const invalidCategories = options.categories.filter(
        (cat: string) => !TOOL_CATEGORIES.includes(cat as ToolCategory)
      );
      
      if (invalidCategories.length > 0) {
        console.error(`Error: Invalid categories: ${invalidCategories.join(', ')}`);
        console.error(`Available categories: ${TOOL_CATEGORIES.join(', ')}`);
        process.exit(1);
      }
      
      enabledCategories = options.categories as ToolCategory[];
    }

    // Determine which transport to use
    let useSSE = false;
    let useHTTP = false;
    
    if (options.transport) {
      if (options.transport.toLowerCase() === 'sse') {
        useSSE = true;
      } else if (options.transport.toLowerCase() === 'http') {
        useHTTP = true;
      } else if (options.transport.toLowerCase() !== 'stdio') {
        console.error(`Error: Invalid transport type: ${options.transport}`);
        console.error(`Available transport types: stdio, sse, http`);
        process.exit(1);
      }
    }
    
    // Prepare server options
    const serverOptions = {
      token,
      enabledCategories,
      transport: options.transport.toLowerCase(),
      httpOptions: useHTTP ? {
        port: options.port === 'default' ? 8080 : parseInt(options.port, 10),
        endpoint: options.endpoint === 'default' ? '/mcp' : options.endpoint
      } : undefined,
      sseOptions: useSSE ? {
        port: options.port === 'default' ? 3000 : parseInt(options.port, 10),
        endpoint: options.endpoint === 'default' ? '/sse' : options.endpoint,
        host: options.host
      } : undefined
    };

    // Start the server
    try {
      // Start the server
      await startServer(serverOptions);
      
      // Add event listeners for errors
      process.on('uncaughtException', (error) => {
        console.error(`Uncaught exception: ${error}`);
      });
      
      process.on('unhandledRejection', (error) => {
        console.error(`Unhandled rejection: ${error}`);
      });
      
    } catch (error) {
      // Report error to stderr to avoid breaking stdio protocol
      console.error('Error starting server:', error);
      process.exit(1);
    }
  });

// Auto-start server when this file is executed directly (not imported)
if (require.main === module) {
  try {
    program.parse();
  } catch (error: unknown) {
    console.error('Error during program execution:', error);
    process.exit(1);
  }
}
