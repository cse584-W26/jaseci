import java.sql.*;
import java.nio.file.*;
public class TpccState {
 public static void main(String[]args)throws Exception{try(Connection c=DriverManager.getConnection(System.getProperty("experiment.mysql.url"),"root","")){TpccGate.state(c,Paths.get(args[0]));}}
}
