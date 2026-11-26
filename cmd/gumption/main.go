// Command gumption is the Gumption server and operator CLI.
//
// Subcommands are added by later features (serve, sim, config, ...); see
// feature_list.json. This file keeps main tiny so the logic stays testable in
// run.
package main

import (
	"fmt"
	"io"
	"os"
	"runtime/debug"
)

// version is the release version, stamped at build time with
// -ldflags "-X main.version=v1.2.3". Unstamped builds report "dev".
var version = "dev"

const usage = `gumption: observability for background task queues

Usage:
  gumption <command>

Commands:
  version   print the version and exit
  help      show this help
`

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

// run executes one CLI invocation and returns the process exit code.
func run(args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 {
		fmt.Fprint(stderr, usage)
		return 2
	}
	switch args[0] {
	case "version", "--version", "-v":
		fmt.Fprintln(stdout, versionString())
		return 0
	case "help", "--help", "-h":
		fmt.Fprint(stdout, usage)
		return 0
	default:
		fmt.Fprintf(stderr, "gumption: unknown command %q\n\n%s", args[0], usage)
		return 2
	}
}

// versionString returns "gumption <version>", adding the VCS revision when
// the binary was built from a git checkout.
func versionString() string {
	s := "gumption " + version
	info, ok := debug.ReadBuildInfo()
	if !ok {
		return s
	}
	var rev, dirty string
	for _, kv := range info.Settings {
		switch kv.Key {
		case "vcs.revision":
			rev = kv.Value
		case "vcs.modified":
			if kv.Value == "true" {
				dirty = "-dirty"
			}
		}
	}
	if len(rev) > 12 {
		rev = rev[:12]
	}
	if rev != "" {
		s += " (" + rev + dirty + ")"
	}
	return s
}
